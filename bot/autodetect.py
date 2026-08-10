"""Deteksi otomatis kontrol pilih & submit di halaman KRS.

Saat recon awal, masa KRS tertutup sehingga checkbox pilih MK dan tombol
submit belum ada di DOM — nilainya `null` di selectors.json. Modul ini
menemukannya sendiri begitu periode dibuka, sehingga tidak perlu inspect
DOM manual di detik-detik war KRS.
"""

from __future__ import annotations

from typing import Any

from playwright.async_api import Page

from bot.config import SELECTORS_PATH, load_selectors
from bot.utils import get_logger, save_json

_SUBMIT_KEYWORDS = ("simpan", "submit", "ambil", "proses", "tambah", "daftar", "save")
_IGNORE_KEYWORDS = ("cetak", "print", "batal", "cancel", "keluar", "logout", "kembali")


async def detect_krs_controls(page: Page) -> dict[str, Any]:
    """Pindai halaman KRS untuk menemukan kontrol pilih & submit."""
    return await page.evaluate(
        """({submitWords, ignoreWords}) => {
            const norm = (s) => (s || '').toString().trim().toLowerCase();
            const out = {
                select_control: null,
                select_kind: null,
                select_count: 0,
                submit: null,
                submit_label: null,
                candidates: {inputs: [], buttons: []},
            };

            const inRow = (el) => !!el.closest('tr');

            // --- Kontrol pilih MK: checkbox di dalam baris tabel ---
            const checkboxes = Array.from(
                document.querySelectorAll("table input[type='checkbox']")
            ).filter(inRow);
            if (checkboxes.length) {
                const names = [...new Set(checkboxes.map(c => c.getAttribute('name')).filter(Boolean))];
                out.select_kind = 'checkbox';
                out.select_count = checkboxes.length;
                if (names.length === 1) {
                    const n = names[0];
                    out.select_control = n.includes('[')
                        ? `input[type='checkbox'][name^='${n.split('[')[0]}']`
                        : `input[type='checkbox'][name='${n}']`;
                } else {
                    out.select_control = "input[type='checkbox']";
                }
            }

            // --- Alternatif: dropdown kelas per baris ---
            if (!out.select_control) {
                const selects = Array.from(document.querySelectorAll('table select')).filter(inRow);
                if (selects.length) {
                    const names = [...new Set(selects.map(s => s.getAttribute('name')).filter(Boolean))];
                    out.select_kind = 'select';
                    out.select_count = selects.length;
                    out.select_control = names.length === 1
                        ? `select[name='${names[0]}']`
                        : 'table select';
                }
            }

            // --- Alternatif: radio / link "ambil" per baris ---
            if (!out.select_control) {
                const radios = Array.from(
                    document.querySelectorAll("table input[type='radio']")
                ).filter(inRow);
                if (radios.length) {
                    out.select_kind = 'radio';
                    out.select_count = radios.length;
                    const n = radios[0].getAttribute('name');
                    out.select_control = n
                        ? `input[type='radio'][name='${n}']`
                        : "input[type='radio']";
                }
            }

            // --- Tombol submit ---
            const controls = Array.from(document.querySelectorAll(
                "input[type='submit'], input[type='button'], button, a.button"
            ));
            for (const el of controls) {
                const label = norm(el.value || el.innerText || el.getAttribute('title'));
                if (!label) continue;
                const entry = {
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type'),
                    name: el.getAttribute('name'),
                    id: el.id || null,
                    label: label.slice(0, 40),
                };
                out.candidates.buttons.push(entry);

                if (ignoreWords.some(w => label.includes(w))) continue;
                if (!submitWords.some(w => label.includes(w))) continue;
                if (out.submit) continue;

                out.submit_label = label;
                if (el.id) {
                    out.submit = `#${el.id}`;
                } else if (el.getAttribute('name')) {
                    const t = el.getAttribute('type');
                    out.submit = t
                        ? `${entry.tag}[name='${el.getAttribute('name')}'][type='${t}']`
                        : `${entry.tag}[name='${el.getAttribute('name')}']`;
                } else if (el.value) {
                    out.submit = `${entry.tag}[value='${el.value}']`;
                }
            }
            return out;
        }""",
        {"submitWords": list(_SUBMIT_KEYWORDS), "ignoreWords": list(_IGNORE_KEYWORDS)},
    )


async def autodetect_and_persist(
    page: Page,
    *,
    selectors: dict[str, Any] | None = None,
    save: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Deteksi kontrol lalu tulis balik ke selectors.json bila ditemukan.

    SIAKAD punya alur 2-langkah:
      1. Halaman KRS: tombol "Tambah Matakuliah" (select_control tidak ada di sini)
      2. Klik -> halaman pilih MK: checkbox + tombol "Tambah"

    Jika di halaman KRS ada tombol "Tambah Matakuliah", anggap KRS terbuka
    meski checkbox belum terlihat (karena belum diklik).
    """
    log = get_logger("autodetect")
    data = selectors or load_selectors()
    detected = await detect_krs_controls(page)

    krs = data.setdefault("krs", {})

    tambah_sel = krs.get("tambah_button") or "input[name='btnProses'][value='Tambah Matakuliah']"
    has_tambah = await page.locator(tambah_sel).count() > 0

    if has_tambah:
        # Alur 2-langkah: checkbox muncul setelah klik Tambah Matakuliah.
        # Set select_control ke nilai yang sudah diketahui dari recon.
        if not krs.get("select_control"):
            krs["select_control"] = "input[type='checkbox'][name='kodeMkul[]']"
            krs["select_kind"] = "checkbox"
            log.info("select_control di-set dari recon: checkbox kodeMkul[] (2-step flow)")
        if not krs.get("submit"):
            krs["submit"] = "input[name='btnAdd'][value='Tambah']"
            log.info("submit di-set dari recon: btnAdd (2-step flow)")
        detected["select_control"] = krs["select_control"]
        detected["submit"] = krs["submit"]
        detected["has_tambah_button"] = True

        if save:
            save_json(SELECTORS_PATH, data)
            log.info(f"selectors.json diperbarui: {SELECTORS_PATH}")
    else:
        # Fallback: coba deteksi langsung di halaman (1-step flow)
        changed = False
        if detected.get("select_control") and not krs.get("select_control"):
            krs["select_control"] = detected["select_control"]
            krs["select_kind"] = detected.get("select_kind")
            changed = True
            log.info(f"select_control terdeteksi: {detected['select_control']}")
        if detected.get("submit") and not krs.get("submit"):
            krs["submit"] = detected["submit"]
            changed = True
            log.info(f"submit terdeteksi: {detected['submit']}")
        if changed and save:
            save_json(SELECTORS_PATH, data)
            log.info(f"selectors.json diperbarui: {SELECTORS_PATH}")

    if not detected.get("select_control") and not has_tambah:
        log.warning("Kontrol pilih MK belum ditemukan di halaman KRS")
    if not detected.get("submit") and not has_tambah:
        log.warning("Tombol submit KRS belum ditemukan di halaman KRS")

    return data, detected
