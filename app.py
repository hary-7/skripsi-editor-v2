#!/usr/bin/env python3
"""
app.py - Antarmuka Streamlit Penyunting & Penyelaras Ritme Naskah Skripsi Bahasa Indonesia.

Mengintegrasikan:
1. Mesin analisis ritme & burstiness: core.metrik_ritme (humanizer-indonesia)
2. Mesin audit EYD V, KBBI, & penanda AI: core.periksa_eyd (naskah-id)
3. Basis pengetahuan lokal: kamus_eyd.json & references/id-ai-tells.md
"""

from __future__ import annotations

import html
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from core import metrik_ritme, periksa_eyd
from core import sintaksis_semantik

# Muat variabel lingkungan (.env)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="Skripsi Editor v2 — Audit EYD V & Penyelaras Ritme",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS Kustom untuk Kartu Metrik, Highlight Teks, dan Tata Letak Dua Kolom
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Kartu Metrik - Dark Mode */
    .metric-card {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px;
        padding: 14px 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8 !important;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #f8fafc !important;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #cbd5e1 !important;
        margin-top: 4px;
    }

    /* Badges */
    .badge-ok {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #064e3b !important;
        color: #6ee7b7 !important;
    }
    .badge-warn {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #78350f !important;
        color: #fde047 !important;
    }
    .badge-err {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #7f1d1d !important;
        color: #fca5a5 !important;
    }

    /* Kotak Sorotan Teks Asli */
    .highlight-box {
        background: #0f172a !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
        padding: 16px;
        line-height: 1.8;
        font-size: 0.95rem;
        color: #e2e8f0 !important;
        max-height: 360px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    .hl-K {
        background-color: #7f1d1d !important;
        color: #fee2e2 !important;
        padding: 2px 6px;
        border-radius: 4px;
        border-bottom: 2px solid #ef4444;
        font-weight: 600;
        cursor: help;
    }
    .hl-AI {
        background-color: #78350f !important;
        color: #fef08a !important;
        padding: 2px 6px;
        border-radius: 4px;
        border-bottom: 2px solid #eab308;
        font-weight: 600;
        cursor: help;
    }
    .hl-G {
        background-color: #1e3a8a !important;
        color: #dbeafe !important;
        padding: 2px 6px;
        border-radius: 4px;
        border-bottom: 2px solid #3b82f6;
        font-weight: 600;
        cursor: help;
    }

    /* Kotak Temuan Panel Audit */
    .audit-item {
        border-left: 4px solid #64748b;
        background: #1e293b !important;
        color: #f1f5f9 !important;
        padding: 10px 14px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
        font-size: 0.88rem;
        line-height: 1.5;
        border-top: 1px solid #334155;
        border-right: 1px solid #334155;
        border-bottom: 1px solid #334155;
    }
    .audit-item code {
        background: #0f172a !important;
        color: #38bdf8 !important;
        padding: 2px 6px;
        border-radius: 4px;
    }
    .audit-item-K { 
        border-left-color: #ef4444 !important; 
        background: #2a1518 !important; 
    }
    .audit-item-AI { 
        border-left-color: #f59e0b !important; 
        background: #2a2012 !important; 
    }
    .audit-item-G { 
        border-left-color: #3b82f6 !important; 
        background: #13233a !important; 
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Pemuatan Sumber Daya: kamus_eyd.json & references/id-ai-tells.md
# ---------------------------------------------------------------------------
CONTOH_NASKAH = (
    "Di era digital ini, perkembangan teknologi informasi memegang peranan yang sangat penting "
    "dalam pengelolaan data akademik. Tidak dapat dipungkiri bahwa sistem informasi universitas "
    "melakukan pengolahan terhadap data mahasiswa secara terus menerus. Dari hasil pengujian "
    "menunjukkan bahwa metode antrian lama masih belum efektif, efisien, dan berkelanjutan. "
    "Selain itu, peneliti melakukan analisa terhadap 120 kuisioner yang di ambil diatas meja "
    "laboratorium pada suhu 25.5 C. Nilai galat mengalami penurunan yang sangat signifikan, "
    "yang mana hal ini membuktikan bahwa sistem baru lebih baik dari sistem lama. "
    "Oleh karena itu, kerjasama antar universitas perlu ditingkatkan agar supaya kwalitas "
    "pelayanan publik semakin handal. Hal ini bukan berarti sistem lama gagal total, melainkan "
    "memerlukan standarisasi lebih lanjut."
)

POLA_TRIKOLON = re.compile(
    r"\b(?:efektif,\s*efisien,\s*dan\s*\w+|cepat,\s*tepat,\s*dan\s*akurat|"
    r"aman,\s*nyaman,\s*dan\s*andal|baik,\s*benar,\s*dan\s*\w+|"
    r"mudah,\s*cepat,\s*dan\s*\w+)\b",
    re.IGNORECASE,
)


@st.cache_data(show_spinner=False)
def muat_kamus_eyd() -> dict[str, Any]:
    jalur = BASE_DIR / "kamus_eyd.json"
    if jalur.exists():
        try:
            return json.loads(jalur.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"kata_baku": {}, "perbaikan_frasa": {}, "konjungsi_awal_kalimat": []}


@st.cache_data(show_spinner=False)
def muat_id_ai_tells() -> str:
    jalur = BASE_DIR / "references" / "id-ai-tells.md"
    if jalur.exists():
        return jalur.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Fungsi Analisis Ritme & Audit EYD + AI Tells
# ---------------------------------------------------------------------------
def analisis_ritme_lengkap(teks: str, preset: str = "akademik") -> dict[str, Any] | None:
    """Hitung metrik ritme dari core.metrik_ritme beserta CV, burstiness, dan sebaran kata."""
    if not teks or not teks.strip():
        return None
    hasil = metrik_ritme.ukur(teks)
    body = metrik_ritme.ambil_prosa(teks)
    kalimat_list = metrik_ritme.pecah_kalimat(body)
    if not kalimat_list:
        # Fallback bila kalimat pendek <= 3 kata semua
        kalimat_list = [k.strip() for k in re.split(r"(?<=[.!?])\s+", body) if k.strip()]
    if not kalimat_list:
        return None

    panjang_per_kalimat = [len(k.split()) for k in kalimat_list]
    if hasil is None:
        rerata = sum(panjang_per_kalimat) / len(panjang_per_kalimat)
        sd = 0.0
        kata = sum(panjang_per_kalimat)
        hasil = {
            "kalimat": len(kalimat_list),
            "kata": kata,
            "rerata": rerata,
            "sd": sd,
            "terpendek": min(panjang_per_kalimat),
            "terpanjang": max(panjang_per_kalimat),
            "pendek_pct": sum(1 for p in panjang_per_kalimat if p <= 10) / len(panjang_per_kalimat) * 100,
            "panjang_pct": sum(1 for p in panjang_per_kalimat if p >= 28) / len(panjang_per_kalimat) * 100,
            "koordinasi": 0.0,
            "n_panjang": sum(1 for p in panjang_per_kalimat if p >= 28),
            "konektor": 0.0,
            "buka_konektor_pct": 0.0,
            "verba_ringan": 0.0,
            "contoh_ringan": [],
            "merupakan": 0,
            "adalah": 0,
            "merupakan_per_1000": 0.0,
            "enum_seperti": 0.0,
            "n_enum": 0,
            "n_rujukan": 0,
            "dimana": 0,
            "yang_mana": 0,
            "frasa_kosong": 0,
            "sangkal": 0,
            "contoh_sangkal": [],
            "dash": 0,
            "en_rentang": 0,
            "pemadat": 0.0,
            "contoh_enum": [],
            "deret": [],
        }

    rerata = float(hasil["rerata"])
    sd = float(hasil["sd"])
    cv = (sd / rerata) if rerata > 0 else 0.0

    # Kategori kalimat untuk diagnostik ritme bertingkat & asimetris (3-7 kata & 20-28 kata)
    pendek_4_7 = sum(1 for p in panjang_per_kalimat if 3 <= p <= 7)
    panjang_20_28 = sum(1 for p in panjang_per_kalimat if 20 <= p <= 28)

    # Tingkat kepadatan kalimat (kombinasi kepadatan kata pemadat & proporsi kalimat panjang)
    pemadat_val = float(hasil.get("pemadat", 0.0))
    panjang_pct = float(hasil.get("panjang_pct", 0.0))
    if pemadat_val < 73:
        label_kepadatan = "Terlalu Mampat"
    elif pemadat_val <= 139 and panjang_pct <= 20.0:
        label_kepadatan = "Proporsional (Wajar)"
    else:
        label_kepadatan = "Padat / Sarat Klausa"

    hasil["cv"] = cv
    hasil["burstiness"] = sd
    hasil["sebaran_kata"] = panjang_per_kalimat
    hasil["daftar_kalimat"] = kalimat_list
    hasil["pendek_4_7"] = pendek_4_7
    hasil["panjang_20_28"] = panjang_20_28
    hasil["label_kepadatan"] = label_kepadatan
    hasil["preset_target"] = metrik_ritme.PRESET.get(preset, metrik_ritme.PRESET["akademik"])
    return hasil


def audit_naskah_lengkap(
    teks: str,
    kamus_tambahan: dict[str, Any],
    filter_kategori: list[str],
) -> list[dict[str, Any]]:
    """
    Gabungkan hasil periksa_eyd.periksa(teks), sintaksis_semantik.audit_sintaksis_semantik(teks),
    kamus_eyd.json, dan pola tambahan dari references/id-ai-tells.md.
    """
    if not teks or not teks.strip():
        return []

    temuan_mentah = periksa_eyd.periksa(teks)
    daftar_temuan: list[dict[str, Any]] = []
    tercatat: set[tuple[int, str, str]] = set()

    for baris, kode, label, cuplikan, saran in temuan_mentah:
        if label not in filter_kategori:
            continue
        kunci = (baris, kode, cuplikan.lower())
        if kunci not in tercatat:
            tercatat.add(kunci)
            daftar_temuan.append(
                {
                    "baris": baris,
                    "kode": kode,
                    "label": label,
                    "cuplikan": cuplikan,
                    "saran": saran,
                }
            )

    # Tambahan pemeriksaan dari kamus_eyd.json yang belum tercakup di periksa_eyd.KATA_BAKU
    kata_baku_json = kamus_tambahan.get("kata_baku", {})
    if "K" in filter_kategori and kata_baku_json:
        for tak_baku, baku in kata_baku_json.items():
            if tak_baku.lower() == baku.lower():
                continue
            for m in re.finditer(r"\b" + re.escape(tak_baku) + r"\b", teks, flags=re.IGNORECASE):
                baris = teks.count("\n", 0, m.start()) + 1
                cuplikan = m.group(0)
                if any(
                    t["baris"] == baris and t["cuplikan"].lower() == cuplikan.lower()
                    for t in daftar_temuan
                ):
                    continue
                daftar_temuan.append(
                    {
                        "baris": baris,
                        "kode": "KB-02",
                        "label": "K",
                        "cuplikan": cuplikan,
                        "saran": f"baku (kamus_eyd.json): {baku}",
                    }
                )

    # Perbaikan frasa dari kamus_eyd.json (mis. "terdiri dari" -> "terdiri atas")
    frasa_json = kamus_tambahan.get("perbaikan_frasa", {})
    if "K" in filter_kategori and "terdiri dari" in frasa_json:
        for m in re.finditer(r"\bterdiri dari\b", teks, flags=re.IGNORECASE):
            baris = teks.count("\n", 0, m.start()) + 1
            cuplikan = m.group(0)
            daftar_temuan.append(
                {
                    "baris": baris,
                    "kode": "EJ-11",
                    "label": "K",
                    "cuplikan": cuplikan,
                    "saran": f"pasangan ungkapan baku: {frasa_json['terdiri dari']}",
                }
            )

    # Tambahan deteksi pola AI dari sintaksis_semantik.py dan references/id-ai-tells.md
    if "AI" in filter_kategori:
        # 0. Integrasi langsung modul sintaksis_semantik (SEM-01, SEM-02, SIN-01, SIN-02, SIN-03)
        temuan_sintaksis = sintaksis_semantik.audit_sintaksis_semantik(teks)
        for baris, kode, _level, cuplikan, saran in temuan_sintaksis:
            kunci = (baris, kode, cuplikan.lower())
            if kunci not in tercatat:
                tercatat.add(kunci)
                daftar_temuan.append(
                    {
                        "baris": baris,
                        "kode": kode,
                        "label": "AI",
                        "cuplikan": cuplikan,
                        "saran": saran,
                    }
                )

        # 1. Trikolon / Tiga sifat berderet (D3 id-ai-tells.md)
        for m in POLA_TRIKOLON.finditer(teks):
            baris = teks.count("\n", 0, m.start()) + 1
            daftar_temuan.append(
                {
                    "baris": baris,
                    "kode": "AI-D3",
                    "label": "AI",
                    "cuplikan": m.group(0),
                    "saran": "Trikolon / tiga sifat berderet (id-ai-tells D3); sisakan satu yang terukur atau ganti dengan angka",
                }
            )

        # 2. Penyangkalan antisipatif (D7 id-ai-tells.md & metrik_ritme.POLA_SANGKAL)
        for m in metrik_ritme.POLA_SANGKAL.finditer(teks):
            baris = teks.count("\n", 0, m.start()) + 1
            daftar_temuan.append(
                {
                    "baris": baris,
                    "kode": "AI-D7",
                    "label": "AI",
                    "cuplikan": " ".join(m.group(0).split()),
                    "saran": "Penyangkalan antisipatif 'bukan X, melainkan Y' / 'bukan berarti' (id-ai-tells D7); nyatakan secara positif",
                }
            )

        # 3. Frasa kosong tambahan dari metrik_ritme.FRASA_KOSONG
        for frasa in metrik_ritme.FRASA_KOSONG:
            for m in re.finditer(r"\b" + re.escape(frasa) + r"\b", teks, flags=re.IGNORECASE):
                baris = teks.count("\n", 0, m.start()) + 1
                cuplikan = m.group(0)
                if any(
                    t["baris"] == baris and cuplikan.lower() in t["cuplikan"].lower()
                    for t in daftar_temuan
                ):
                    continue
                daftar_temuan.append(
                    {
                        "baris": baris,
                        "kode": "AI-B2",
                        "label": "AI",
                        "cuplikan": cuplikan,
                        "saran": "Intensifier / frasa kosong (id-ai-tells B2); hapus atau ganti dengan data terukur",
                    }
                )

        # 4. Em dash (—) atau En dash (–) di badan prosa
        for m in re.finditer(r"\u2014|(?<!\d)\u2013|\u2013(?!\d)", teks):
            baris = teks.count("\n", 0, m.start()) + 1
            daftar_temuan.append(
                {
                    "baris": baris,
                    "kode": "AI-DASH",
                    "label": "AI",
                    "cuplikan": m.group(0),
                    "saran": "Hindari em dash/en dash di badan prosa (id-ai-tells); gunakan koma, titik dua, atau pecah kalimat",
                }
            )

    daftar_temuan.sort(key=lambda x: (x["baris"], x["kode"]))
    return daftar_temuan


def sorot_teks_html(teks: str, temuan: list[dict[str, Any]]) -> str:
    """Bangun HTML dengan sorotan langsung pada cuplikan kata/frasa yang melanggar kaidah/AI/gaya."""
    if not teks:
        return ""
    if not temuan:
        return f'<div class="highlight-box">{html.escape(teks)}</div>'

    # Kumpulkan rentang karakter (start, end, label, kode, saran) di dalam teks
    rentang_temuan: list[tuple[int, int, str, str, str]] = []
    prioritas_label = {"K": 3, "AI": 2, "G": 1}

    for item in temuan:
        cuplikan = item["cuplikan"].replace(" …", "").strip()
        if not cuplikan or len(cuplikan) < 2:
            continue
        pola_cari = re.escape(cuplikan)
        # Dukungan penanda pemisah klausa '[,]' (SIN-03) & '...' (SIN-05) dari sintaksis_semantik
        pola_cari = (
            pola_cari.replace(r"\[\,\]", r"[,;]")
            .replace(r"\[,\]", r"[,;]")
            .replace(r"\.\.\.", r"[^.!?]{1,120}[.!?]\s+")
        )
        # Longgarkan spasi agar cocok dengan pemisahan baris
        pola_cari = re.sub(r"\\\s+", r"\\s*", pola_cari)
        try:
            for m in re.finditer(pola_cari, teks, flags=re.IGNORECASE):
                rentang_temuan.append(
                    (m.start(), m.end(), item["label"], item["kode"], item["saran"])
                )
        except re.error:
            continue

    if not rentang_temuan:
        return f'<div class="highlight-box">{html.escape(teks)}</div>'

    # Urutkan berdasarkan posisi mulai, lalu panjang menurun, lalu prioritas label
    rentang_temuan.sort(
        key=lambda r: (r[0], -(r[1] - r[0]), -prioritas_label.get(r[2], 0))
    )

    # Saring tumpang tindih
    rentang_bersih: list[tuple[int, int, str, str, str]] = []
    batas_akhir = -1
    for start, end, label, kode, saran in rentang_temuan:
        if start >= batas_akhir:
            rentang_bersih.append((start, end, label, kode, saran))
            batas_akhir = end

    potongan: list[str] = []
    kursor = 0
    for start, end, label, kode, saran in rentang_bersih:
        if start > kursor:
            potongan.append(html.escape(teks[kursor:start]))
        teks_asli = html.escape(teks[start:end])
        tooltip = html.escape(f"[{kode} - {label}] {saran}", quote=True)
        kelas = f"hl-{label}" if label in ("K", "AI", "G") else "hl-K"
        potongan.append(
            f'<span class="{kelas}" title="{tooltip}">{teks_asli}</span>'
        )
        kursor = end
    if kursor < len(teks):
        potongan.append(html.escape(teks[kursor:]))

    return f'<div class="highlight-box">{"".join(potongan)}</div>'


# ---------------------------------------------------------------------------
# Mesin Perombakan: Prompt Bertingkat, Groq Cloud, Ollama Lokal, & Rule-Based
# ---------------------------------------------------------------------------
def bangun_prompt_perombakan(
    teks: str,
    metrik: dict[str, Any] | None,
    temuan: list[dict[str, Any]],
    target_cv: float,
    preset: str = "akademik",
) -> str:
    """Susun prompt sistem & instruksi perombakan ritme asimetris berbasis audit sintaksis-semantik."""
    ringkasan_audit = []
    for t in temuan[:25]:
        ringkasan_audit.append(
            f"- [{t['kode']} ({t['label']})] '{t['cuplikan']}' -> {t['saran']}"
        )
    daftar_audit_str = (
        "\n".join(ringkasan_audit)
        if ringkasan_audit
        else "- Tidak ada pelanggaran ejaan utama; fokuskan pada restrukturisasi ritme asimetris."
    )

    cv_sekarang = f"{metrik['cv']:.2f}" if metrik else "0.00"
    rerata_sekarang = f"{metrik['rerata']:.1f}" if metrik else "0.0"
    sd_sekarang = f"{metrik['sd']:.1f}" if metrik else "0.0"

    return f"""Anda adalah penyunting senior karya ilmiah Bahasa Indonesia (setara editor jurnal SINTA 1 & pendamping skripsi) yang menguasai EYD Edisi V, KBBI VI, humanizer-indonesia, dan aturan sintaksis-semantik anti-pola AI.

TUGAS UTAMA:
Rombak dan selaraskan naskah draf skripsi berikut agar memiliki karakter tulisan peneliti manusia seutuhnya, lolos uji ritme asimetris (Koefisien Variasi / CV >= {target_cv:.2f}), bebas dari prediktabilitas leksikal/kolokasi klise AI, dan patuh penuh pada EYD V & KBBI.

PROFIL NASKAH SAAT INI:
- Register sasaran: {preset.upper()}
- Rata-rata panjang kalimat: {rerata_sekarang} kata (Simpangan baku: {sd_sekarang} kata, CV saat ini: {cv_sekarang})

DAFTAR TEMUAN AUDIT YANG WAJIB DIPERBAIKI:
{daftar_audit_str}

ATURAN RESTRUKTURISASI RITME ASIMETRIS & ANTI-POLA AI (WAJIB DITERAPKAN):
1. RESTRUKTURISASI RITME ASIMETRIS (Target CV >= {target_cv:.2f}):
   - Selingi KALIMAT PENDEK (3-7 kata) yang deklaratif dan tegas untuk menyatakan temuan inti, fakta kunci, atau simpulan langsung (contoh: "Galat pengukuran turun drastis." atau "Efisiensinya sendiri masih rendah.").
   - Padukan dengan KALIMAT PANJANG (20-28 kata) beranak kalimat bertingkat (memakai konjungsi subordinatif 'sehingga', 'karena', 'meskipun', 'apabila') untuk menguraikan mekanisme, sebab-akibat, atau analisis metodologis.
   - Hindari simetri klausa mekanis (dua klausa yang dipisahkan koma dengan jumlah kata hampir persis sama, misal 10 kata vs 10 kata). Gunakan variasi sintaksis, inversi ilmiah, atau verba pasif yang wajar agar tidak selalu berpola Subjek di awal kalimat.
2. LARANGAN TRIKOLON KLAUSA & KOLOKASI KLISE (sintaksis_semantik):
   - Dilarang menyusun trikolon klausa aktif (deret 3 verba berawalan me- sejajar dalam satu kalimat) maupun trikolon preposisi tujuan (deret 3 'untuk/guna/demi' berseri); pecah klausa ketiga menjadi kalimat terpisah.
   - Bersihkan seluruh kolokasi klise AI: 'kontribusi signifikan/nyata', 'landasan fundamental/kokoh', 'pemahaman komprehensif/holistik', 'peran krusial/vital/strategis', 'dinamika berkembang/kompleks', 'tantangan tersendiri', 'langkah strategis', 'implikasi luas', 'memberikan wawasan baru'. Ganti dengan fungsi atau dampak teknis yang terukur.
   - Hapus penumpukan modalitas/hedging ganda ('tampaknya dapat dikatakan', 'cenderung berpotensi', 'diduga kemungkinan besar', 'mungkin dapat diindikasikan').
3. LARANGAN PENUTUP HARAPAN NORMATIF & KLISE WACANA (id-ai-tells.md):
   - Jangan menutup paragraf dengan kalimat harapan normatif klise ('Diharapkan penelitian ini dapat...', 'secara berkelanjutan'). Akhiri dengan simpulan data konkret atau batas temuan.
   - Hapus pembuka kosmik ('Di era digital ini', 'Seiring perkembangan zaman', 'Tidak dapat dipungkiri bahwa') dan penyangkalan antisipatif ('bukan berarti...', 'bukan X, melainkan Y').
   - Ubah nominalisasi/verba ringan ('melakukan pengukuran terhadap', 'mengalami penurunan') menjadi verba langsung ('mengukur', 'turun', 'dianalisis'). Jangan gunakan em dash (—) atau en dash (–) di badan kalimat.
4. KEPATUHAN EYD V & INTEGRITAS DATA ILMIAH:
   - Perbaiki seluruh kata tidak baku KBBI dan pemisahan kata depan 'di'/'ke' vs awalan 'di-'.
   - PERTAHANKAN 100% seluruh angka, satuan (desimal memakai koma sesuai EYD V, misal 25,5 °C), nama dokumen resmi, sitasi penulis, dan tahun terbit.

KELUARAN:
Tuliskan HANYA naskah hasil perombakan akhir yang siap tempel ke dokumen skripsi, tanpa kata pengantar, tanpa blok kode markdown, dan tanpa penjelasan tambahan.

NASKAH ASLI:
{teks}"""


def rombak_aturan_standar(
    teks: str,
    kamus_tambahan: dict[str, Any],
    target_cv: float = 0.45,
) -> str:
    """
    Mesin Perombakan Aturan Standar (Rule-Based Tanpa AI):
    1. Koreksi kata baku (periksa_eyd.KATA_BAKU + kamus_eyd.json)
    2. Perbaikan ejaan EYD V (awalan di-, kata depan di/ke, angka desimal & satuan, koma sebelum sehingga)
    3. Pembersihan klise AI, kolokasi klise, hedging bertumpuk, trikolon antarklausa, dan penutup normatif (sintaksis_semantik)
    4. Penyelarasan ritme asimetris (selang-seling kalimat pendek 3-7 kata & panjang 20-28 kata)
    """
    if not teks or not teks.strip():
        return ""

    hasil = teks

    # 1. Hapus em dash dan en dash non-angka di badan prosa
    hasil = hasil.replace("\u2014", ", ")
    hasil = re.sub(r"(?<!\d)\s*\u2013\s*(?!\d)", ", ", hasil)

    # 2. Bersihkan pembuka kosmik, frasa kosong, & penutup harapan normatif
    pembuka_dan_penutup_klise = [
        (r"(?:^|(?<=[.!?]\s))Di era (?:digital|modern|globalisasi|teknologi)[^,]{0,30},\s*", ""),
        (r"(?:^|(?<=[.!?]\s))Seiring (?:dengan )?(?:perkembangan|kemajuan) (?:zaman|teknologi|waktu)[^,]{0,35},\s*", ""),
        (r"\b[Tt](?:idak|ak) dapat dipungkiri bahwa\s+", ""),
        (r"\b[Ss]eperti yang (?:kita )?(?:ketahui|diketahui) bersama(?:,\s*|\s+bahwa\s+|\s+)", ""),
        (r"\b[Pp]erlu diingat bahwa\s+", ""),
        (r"\b[Mm]ari kita\s+", ""),
        # Penutup harapan normatif klise AI
        (
            r"(?:^|(?<=[.!?]\s))(?:Dengan demikian,\s*)?[Dd]iharapkan\s+(?:hasil\s+)?(?:penelitian|kajian|studi|sistem)\s+ini\s+dapat\s+memberikan\s+([^.!?]+)[.!?]",
            r"Temuan ini memperlihatkan \1.",
        ),
        (r"\b[Dd]iharapkan\s+dapat\s+", "dapat "),
    ]
    for pola, ganti in pembuka_dan_penutup_klise:
        hasil = re.sub(pola, ganti, hasil)

    # 2b. Bersihkan kolokasi klise AI & hedging bertumpuk sesuai modul sintaksis_semantik
    perbaikan_kolokasi_dan_hedging = [
        # KOLOKASI_KLISE & Adverbia Evaluatif Kosong (SEM-01)
        (r"\bkontribusi\s+(?:yang\s+)?(?:signifikan|nyata|positif|substansial)\b", "dampak terukur"),
        (r"\blandasan\s+(?:yang\s+)?(?:fundamental|kokoh|krusial)\b", "dasar teoretis"),
        (r"\bpemahaman\s+(?:yang\s+)?(?:komprehensif|mendalam|holistik)\b", "batasan analisis yang jelas"),
        (r"\bperan\s+(?:yang\s+)?(?:krusial|vital|sentral|strategis)\b", "fungsi teknis utama"),
        (r"\bdinamika\s+(?:yang\s+)?(?:berkembang|kompleks)\b", "perubahan fenomena yang diamati"),
        (r"\btantangan\s+tersendiri\b", "kendala teknis di lapangan"),
        (r"\blangkah\s+(?:yang\s+)?strategis\b", "tahapan metodologis"),
        (r"\bimplikasi\s+(?:yang\s+)?luas\b", "implikasi praktis"),
        (r"\bsecara\s+berkelanjutan\b", "secara konsisten"),
        (r"\bmemberikan\s+wawasan\s+(?:baru)?\b", "memperlihatkan temuan"),
        (r"\s*\bsecara\s+(?:holistik|komprehensif|substansial)\b", ""),
        (r"\bsecara\s+(?:masif|eksponensial)\b", "secara terukur"),
        (r"\bsangat\s+optimal\b", "optimal"),
        # KALKE RETORIS "tidak hanya X, tetapi juga Y" (SIN-04)
        (
            r"\b(?:tidak\s+hanya|bukan\s+hanya)\s+([^.,;]{3,50}),\s*(?:tetapi|melainkan)\s+(?:juga\s+)?([^.,;]{3,50})\b",
            r"\1 serta \2",
        ),
        # ANTROPOMORFISME METODOLOGIS (SEM-03)
        (
            r"\b(penelitian|skripsi|kajian|tabel|grafik|data)\s+ini\s+(?:mencoba|berusaha|ingin|berharap)\s+(?:untuk\s+)?(memahami|mengungkap|membuktikan|menjelaskan)\b",
            r"\1 ini difokuskan untuk \2",
        ),
        # PENUTUP PARAGRAF HARAPAN NORMATIF (SEM-04)
        (
            r"\b(?:diharapkan|perlu\s+adanya|langkah\s+ini\s+dapat\s+membawa)\s+([^.!?]+?)(?:kemajuan|manfaat|dampak\s+positif|masa\s+depan)\b",
            r"temuan ini menegaskan \1perbaikan terukur",
        ),
        # HEDGING_BERTUMPUK (SEM-02)
        (r"\b(?:tampaknya|sepertinya)\s+(?:dapat\s+dikatakan|dapat\s+disimpulkan)\s+bahwa\b", "Hasil menunjukkan bahwa"),
        (r"\b(?:tampaknya|sepertinya)\s+(?:dapat\s+dikatakan|dapat\s+disimpulkan)\b", "terlihat"),
        (r"\bdapat\s+disimpulkan\s+bahwa\b", "hasil menunjukkan bahwa"),
        (r"\bcenderung\s+(?:berpotensi|memiliki\s+kecenderungan)\b", "berpotensi"),
        (r"\bdiduga\s+(?:kuat\s+)?(?:kemungkinan\s+besar)\b", "diduga"),
        (r"\bmungkin\s+dapat\s+diindikasikan\b", "mengindikasikan"),
    ]
    for pola, ganti in perbaikan_kolokasi_dan_hedging:
        hasil = re.sub(pola, ganti, hasil, flags=re.IGNORECASE)

    # 2c. Pecah Trikolon Antarklausa (SIN-01: 3 verba me- sejajar & SIN-02: 3 preposisi untuk/guna/demi sejajar)
    hasil = re.sub(
        r"\b(me[a-z]{3,}\s+[^,;.]{4,40}),\s+(me[a-z]{3,}\s+[^,;.]{4,40}),\s+(?:dan|serta)\s+(me[a-z]{3,}\b[^.!?]*)",
        r"\1 dan \2. Selanjutnya, proses ini \3",
        hasil,
        flags=re.IGNORECASE,
    )
    hasil = re.sub(
        r"\b((?:untuk|guna|demi)\s+[^,;.]{4,40}),\s+((?:untuk|guna|demi)\s+[^,;.]{4,40}),\s+(?:dan|serta)\s+((?:untuk|guna|demi)\b[^.!?]*)",
        r"\1 serta \2. Langkah ini juga ditujukan \3",
        hasil,
        flags=re.IGNORECASE,
    )

    # 3. Perbaiki konstruksi kalimat tidak efektif & pleonasme (KE-01 s.d. KE-17)
    perbaikan_konstruksi = [
        (
            r"(^|(?<=[.!?]\s))(?:Dari|Dalam|Pada)\s+(hasil\s+\w+|penelitian\s+ini|pengujian\s+ini)\s+(menunjukkan|membahas|memperlihatkan|menjelaskan|menyimpulkan|membuktikan)\b",
            lambda m: f"{m.group(1)}{m.group(2).capitalize()} {m.group(3)}",
        ),
        (r"\badalah merupakan\b", "merupakan"),
        (r"\bagar supaya\b", "agar"),
        (r"\bdemi untuk\b", "untuk"),
        (r"\bsejak dari\b", "sejak"),
        (r"\bsangat\s+(\w+)\s+sekali\b", r"sangat \1"),
        (r"\bberbagai macam\b", "berbagai"),
        (r"\bberdasarkan pada\b", "berdasarkan"),
        (r"\bterdiri dari\b", "terdiri atas"),
        (r"\bmemainkan peranan penting\b", "berperan penting"),
        (r"\bmemainkan peran\b", "berperan"),
        (r"\bmengambil tempat\b", "berlangsung"),
        (r"\bmemegang peranan (?:yang )?(?:sangat )?(?:penting|krusial|vital|sentral)\b", "berperan penting"),
        (r"\bsangat signifikan\b", "signifikan"),
        (r",\s*yang mana\s+(?:hal ini\s+)?", " sehingga "),
        (r"\byang mana\b", "yang"),
        (r",\s*di mana\s+", " tempat "),
        (r"\bdimana\b", "tempat"),
        # Nominalisasi / verba ringan umum
        (r"\bmelakukan\s+pengolahan\s+terhadap\b", "mengolah"),
        (r"\bmelakukan\s+pengukuran\s+terhadap\b", "mengukur"),
        (r"\bmelakukan\s+(?:analisis|analisa)\s+terhadap\b", "menganalisis"),
        (r"\bmelakukan\s+pengujian\s+terhadap\b", "menguji"),
        (r"\bmelaksanakan\s+pengujian\b", "menguji"),
        (r"\bmengalami\s+penurunan\s+yang\b", "turun secara"),
        (r"\bmengalami\s+peningkatan\s+yang\b", "naik secara"),
        (r"\bmengalami\s+penurunan\b", "turun"),
        (r"\bmengalami\s+peningkatan\b", "naik"),
        (r"\bmemberikan\s+pengaruh\s+terhadap\b", "memengaruhi"),
        (r"\bmemberikan\s+kontribusi\s+terhadap\b", "berperan dalam"),
        (r"\bterus\s+menerus\b", "terus-menerus"),
        (r"\bmembuktikan\s+bahwa\b", "menunjukkan bahwa"),
        # Trikolon klise -> lugas
        (r"\befektif,\s*efisien,\s*dan\s*(?:berkelanjutan|\w+)\b", "efektif"),
        (r"\bcepat,\s*tepat,\s*dan\s*akurat\b", "akurat"),
        (r"\baman,\s*nyaman,\s*dan\s*andal\b", "andal"),
        # Penyangkalan antisipatif -> positif
        (
            r"\bHal ini bukan berarti\s+([^,]+),\s*melainkan\s+",
            r"Meskipun belum menunjukkan bahwa \1, kondisi ini ",
        ),
        (r"\bbukan berarti\b", "belum tentu menandakan bahwa"),
        # Perbandingan "lebih ... dari " -> "lebih ... daripada "
        (r"\blebih\s+(?!dari\b)(\w+)\s+dari\b(?!\s+(?:pada|sekadar)\b)", r"lebih \1 daripada"),
        # EYD V: tanpa koma sebelum sehingga
        (r",\s+sehingga\b", " sehingga"),
    ]
    for pola, ganti in perbaikan_konstruksi:
        hasil = re.sub(pola, ganti, hasil, flags=re.IGNORECASE)

    # 4. Perbaiki awalan di- yang dipisah & kata depan di/ke yang dirangkai
    hasil = re.sub(
        r"\bdi\s+(analisis|analisa|uji|lakukan|gunakan|ukur|ambil|peroleh|buat|hitung|kembangkan|rancang|teliti|bahas|amati|olah|kumpulkan|terapkan|jelaskan|tentukan|sajikan|tampilkan)\b",
        lambda m: "di" + m.group(1).lower(),
        hasil,
        flags=re.IGNORECASE,
    )
    kata_depan_tempat = (
        "atas|bawah|dalam|luar|depan|belakang|samping|antara|sini|sana|situ"
    )
    hasil = re.sub(
        rf"\b(di|ke)({kata_depan_tempat})\b",
        lambda m: f"{m.group(1)} {m.group(2)}",
        hasil,
        flags=re.IGNORECASE,
    )
    hasil = re.sub(r"\bkerjasama\b", "kerja sama", hasil, flags=re.IGNORECASE)
    hasil = re.sub(r"\btanggungjawab\b", "tanggung jawab", hasil, flags=re.IGNORECASE)
    hasil = re.sub(r"\bbertanggungjawab\b", "bertanggung jawab", hasil, flags=re.IGNORECASE)

    # 5. Gabungan kata terikat (antar, pasca, sub, non, multi, pra)
    hasil = re.sub(
        r"\b(antar|pasca|non|multi|sub|pra)\s+([a-z]{3,})\b",
        lambda m: m.group(1) + m.group(2),
        hasil,
        flags=re.IGNORECASE,
    )

    # 6. Kata baku dari periksa_eyd.KATA_BAKU + kamus_eyd.json
    semua_kata_baku = dict(periksa_eyd.KATA_BAKU)
    for k_tb, k_b in kamus_tambahan.get("kata_baku", {}).items():
        # Catatan: di kamus_eyd.json ada "metodologi": "metode", jangan ubah bila metodologi memang dimaksudkan kecuali kata tak baku
        if k_tb not in ("perilaku", "ijazah", "metodologi"):
            semua_kata_baku[k_tb.lower()] = k_b

    pola_kb_gabungan = re.compile(
        r"\b(" + "|".join(sorted(map(re.escape, semua_kata_baku.keys()), key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )

    def _ganti_baku(m: re.Match[str]) -> str:
        asli = m.group(0)
        pengganti = semua_kata_baku.get(asli.lower(), asli)
        if asli[0].isupper() and pengganti[0].islower():
            return pengganti.capitalize()
        return pengganti

    hasil = pola_kb_gabungan.sub(_ganti_baku, hasil)

    # 7. EYD V: angka desimal titik -> koma pada satuan & lambang suhu C -> °C
    hasil = re.sub(
        r"\b(\d+)\.(\d{1,2})\s*(%|V|mV|kV|A|mA|W|kW|Hz|kHz|MHz|kg|g|mg|cm|mm|km|m|s|ms|°C|C)\b",
        r"\1,\2 \3",
        hasil,
    )
    hasil = re.sub(r"\b(\d+(?:,\d+)?)\s*C\b", r"\1 °C", hasil)

    # 8. Penyelarasan ritme bertingkat (selang-seling kalimat pendek 4-7 kata & panjang 20-28 kata)
    paragraf_baru: list[str] = []
    for par in hasil.split("\n\n"):
        if not par.strip():
            continue
        kalimat_list = metrik_ritme.pecah_kalimat(par)
        if not kalimat_list:
            paragraf_baru.append(par.strip())
            continue

        kalimat_hasil: list[str] = []
        for kal in kalimat_list:
            kal = kal.strip()
            if kal and kal[0].islower():
                kal = kal[0].upper() + kal[1:]
            kata_kal = kal.split()
            n_kata = len(kata_kal)

            # Jika kalimat terlalu panjang (> 28 kata) atau berada di zona monoton (12-19 kata terus-menerus),
            # pecah pada konjungsi 'sehingga' / 'karena' / 'namun' bila memungkinkan agar menghasilkan pasangan pendek + sedang/panjang
            if n_kata > 26:
                pecah_konj = re.split(
                    r"\s+(?=sehingga\b|karena\b|namun\b|sedangkan\b)",
                    kal,
                    maxsplit=1,
                )
                if len(pecah_konj) == 2 and len(pecah_konj[0].split()) >= 5:
                    bag1 = pecah_konj[0].rstrip(",. ") + "."
                    bag2 = pecah_konj[1].strip()
                    bag2 = re.sub(
                        r"^(?:sehingga|namun|sedangkan),?\s*",
                        lambda m: (
                            "Akibatnya, "
                            if m.group(0).lower().startswith("sehingga")
                            else "Namun, "
                        ),
                        bag2,
                        flags=re.IGNORECASE,
                    )
                    if bag2 and bag2[0].islower():
                        bag2 = bag2[0].upper() + bag2[1:]
                    kalimat_hasil.extend([bag1, bag2])
                    continue

            kalimat_hasil.append(kal)

        # Periksa CV sementara; bila semua kalimat menumpuk di rentang menengah (mis. 10-18 kata),
        # gabungkan dua kalimat menengah dengan konjungsi subordinatif (20-28 kata) dan ringkas satu kalimat menjadi tegas (4-7 kata)
        panjang_skr = [len(k.split()) for k in kalimat_hasil]
        if len(kalimat_hasil) >= 3:
            rerata_skr = sum(panjang_skr) / len(panjang_skr)
            sd_skr = (
                (sum((x - rerata_skr) ** 2 for x in panjang_skr) / len(panjang_skr)) ** 0.5
                if rerata_skr > 0
                else 0.0
            )
            cv_skr = sd_skr / rerata_skr if rerata_skr > 0 else 0.0
            if cv_skr < target_cv:
                # Cari dua kalimat berurutan yang panjangnya 9-15 kata untuk difusi menjadi kalimat panjang 20-28 kata
                diubah: list[str] = []
                idx = 0
                sudah_fusi = False
                while idx < len(kalimat_hasil):
                    k_ini = kalimat_hasil[idx]
                    w_ini = len(k_ini.split())
                    if (
                        not sudah_fusi
                        and idx + 1 < len(kalimat_hasil)
                        and 8 <= w_ini <= 16
                        and 8 <= len(kalimat_hasil[idx + 1].split()) <= 16
                    ):
                        k_lanjut = kalimat_hasil[idx + 1].lstrip()
                        # Bersihkan penghubung awal kalimat kedua bila ada
                        k_lanjut_bersih = re.sub(
                            r"^(?:Selain itu|Oleh karena itu|Namun|Dengan demikian|Akibatnya),\s*",
                            "",
                            k_lanjut,
                            flags=re.IGNORECASE,
                        )
                        if k_lanjut_bersih:
                            k_lanjut_bersih = (
                                k_lanjut_bersih[0].lower() + k_lanjut_bersih[1:]
                            )
                        gabung = (
                            k_ini.rstrip(".!?")
                            + " sehingga "
                            + k_lanjut_bersih
                        )
                        diubah.append(gabung)
                        sudah_fusi = True
                        idx += 2
                        continue
                    diubah.append(k_ini)
                    idx += 1
                kalimat_hasil = diubah

                # Pastikan ada kalimat pendek (4-7 kata) untuk temuan tegas & kalimat panjang (20-28 kata)
                for j, k_item in enumerate(list(kalimat_hasil)):
                    m_temuan = re.match(
                        r"^([^,.]{15,45}?)\s+sehingga\s+(menunjukkan\s+bahwa\s+.+)$",
                        k_item,
                        flags=re.IGNORECASE,
                    )
                    if m_temuan and 4 <= len(m_temuan.group(1).split()) <= 7:
                        kalimat_hasil[j] = m_temuan.group(1).strip().rstrip(".") + "."
                        kalimat_hasil.insert(
                            j + 1,
                            "Temuan ini " + m_temuan.group(2).strip(),
                        )
                        break

                # Cari kalimat dengan "Oleh karena itu, X perlu ditingkatkan agar Y" -> pecah menjadi kalimat pendek tegas (4-7 kata) + kalimat majemuk (20-28 kata)
                for j, k_item in enumerate(list(kalimat_hasil)):
                    m_agar = re.match(
                        r"^(?:Oleh karena itu,\s*)?(.{15,65}?)\s+agar\s+(.+)$",
                        k_item,
                        flags=re.IGNORECASE,
                    )
                    if m_agar:
                        inti = m_agar.group(1).strip().rstrip(".")
                        if inti and inti[0].islower():
                            inti = inti[0].upper() + inti[1:]
                        tujuan = m_agar.group(2).strip().rstrip(".")
                        kalimat_hasil[j] = f"{inti}."
                        if j + 1 < len(kalimat_hasil):
                            lanjut = kalimat_hasil[j + 1].lstrip()
                            lanjut_kecil = lanjut[0].lower() + lanjut[1:] if lanjut else ""
                            kalimat_hasil[j + 1] = (
                                f"Langkah tersebut ditempuh agar {tujuan}, terlebih {lanjut_kecil}"
                            )
                        else:
                            kalimat_hasil.insert(
                                j + 1,
                                f"Langkah tersebut ditempuh agar {tujuan}.",
                            )
                        break

                # Pecah atau hilangkan koma pada simetri klausa mekanis (SIN-03: 2 klausa >=8 kata dengan selisih <=1 kata)
                kalimat_asimetris: list[str] = []
                for k_uji in kalimat_hasil:
                    klausa_uji = [
                        kl.strip()
                        for kl in re.split(r",|;\s*", k_uji)
                        if len(kl.strip().split()) >= 4
                    ]
                    if len(klausa_uji) == 2:
                        l1 = len(klausa_uji[0].split())
                        l2 = len(klausa_uji[1].split())
                        if l1 >= 8 and l2 >= 8 and abs(l1 - l2) <= 1:
                            # Hilangkan simetri koma dengan mengganti pemisah atau memecah kalimat
                            k_uji = re.sub(r",\s+", " sehingga ", k_uji, count=1)
                    kalimat_asimetris.append(k_uji)
                kalimat_hasil = kalimat_asimetris

        # Tangani kegagalan pelesapan subjek pada 2 kalimat berurutan (SIN-05)
        pola_subjek_ulang = re.compile(
            r"^(?:Penelitian|Metode|Sistem|Pengujian|Kajian)\s+(?:ini|tersebut)\s+",
            re.IGNORECASE,
        )
        for idx_s in range(len(kalimat_hasil) - 1):
            if pola_subjek_ulang.match(kalimat_hasil[idx_s]) and pola_subjek_ulang.match(
                kalimat_hasil[idx_s + 1]
            ):
                kalimat_hasil[idx_s + 1] = pola_subjek_ulang.sub(
                    "Penerapannya ", kalimat_hasil[idx_s + 1], count=1
                )

        paragraf_baru.append(" ".join(kalimat_hasil))

    return "\n\n".join(paragraf_baru)


# ---------------------------------------------------------------------------
# Konfigurasi Router9 API & Kamus 5 Model
# ---------------------------------------------------------------------------
ROUTER9_ENDPOINT = "https://api.router9.com/v1/chat/completions"

ROUTER9_MODELS: dict[str, str] = {
    "Router9: Qwen3 235B (Bahasa Alami & Luwes)": "qwen/qwen3-235b-a22b-2507",
    "Router9: DeepSeek V4 Pro (Akurasi & Logika)": "deepseek/deepseek-v4-pro",
    "Router9: DeepSeek V4 Flash (Super Cepat)": "deepseek/deepseek-v4-flash",
    "Router9: GLM 5.2 (Objektif & Lugas)": "z-ai/glm-5.2",
    "Router9: MiniMax M3 (Diksi Alternatif)": "minimax/minimax-m3",
}


def ambil_router9_api_key_awal() -> str:
    """Ambil kunci API Router9 dari st.secrets['ROUTER9_API_KEY'] atau os.getenv('ROUTER9_API_KEY', '')."""
    try:
        if "ROUTER9_API_KEY" in st.secrets:
            return str(st.secrets["ROUTER9_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("ROUTER9_API_KEY", "").strip()


def panggil_router9(model_id: str, prompt_teks: str) -> str:
    """
    Panggil endpoint OpenAI-compatible Router9 API (https://api.router9.com/v1/chat/completions)
    dengan timeout 60 detik dan penanganan galat yang jelas di UI.
    """
    api_key = (
        st.session_state.get("router9_api_key_input", "").strip()
        or ambil_router9_api_key_awal()
    )
    if not api_key or api_key.startswith("kunci_"):
        st.warning(
            "⚠️ Kunci API Router9 (`ROUTER9_API_KEY`) belum disetel. Silakan masukkan kunci API Router9 di bilah samping (Sidebar) atau tambahkan ke berkas `.env` / `st.secrets`."
        )
        return ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Anda adalah penyunting senior karya ilmiah Bahasa Indonesia. "
                    "Patuhi kaidah EYD V, bentuk ritme asimetris (CV >= 0.45), "
                    "hapus klise AI, dan jaga integritas 100% fakta/angka."
                ),
            },
            {"role": "user", "content": prompt_teks},
        ],
        "temperature": 0.3,
    }

    try:
        resp = requests.post(
            ROUTER9_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            st.warning(
                f"⚠️ Router9 API (`{model_id}`) mengembalikan status {resp.status_code}: {resp.text[:250]}"
            )
            return ""
        data = resp.json()
        pilihan = data.get("choices") or []
        if not pilihan:
            st.warning(f"⚠️ Respons Router9 API (`{model_id}`) tidak memuat hasil teks.")
            return ""
        teks_keluaran = (pilihan[0].get("message", {}).get("content") or "").strip()
        teks_keluaran = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", teks_keluaran).strip()
        return teks_keluaran
    except Exception as exc:
        st.warning(f"⚠️ Gagal menghubungi Router9 API (`{model_id}`): {exc}")
        return ""


def panggil_groq_cloud(prompt: str, api_key: str) -> tuple[bool, str, str]:
    """
    Panggil Groq Cloud dengan model utama 'llama-3.3-70b-versatile' (dan fallback 'openai/gpt-oss-20b').
    """
    if not api_key or api_key.startswith("kunci_"):
        return (
            False,
            "",
            "GROQ_API_KEY belum diatur di berkas `.env` atau bilah pengaturan.",
        )

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        daftar_model = ["llama-3.3-70b-versatile", "openai/gpt-oss-20b"]
        galat_terakhir = ""

        for nama_model in daftar_model:
            try:
                resp = client.chat.completions.create(
                    model=nama_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Anda adalah editor akademik Bahasa Indonesia ahli EYD V, KBBI, "
                                "dan penyelarasan ritme kalimat ilmiah. Keluarkan hanya teks hasil suntingan."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.45,
                    max_tokens=2048,
                )
                teks_keluaran = (resp.choices[0].message.content or "").strip()
                # Bersihkan bila dibungkus kutipan/markdown
                teks_keluaran = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", teks_keluaran).strip()
                if teks_keluaran:
                    return True, teks_keluaran, f"Groq Cloud ({nama_model})"
            except Exception as exc:
                galat_terakhir = str(exc)
                continue

        return False, "", f"Gagal memanggil Groq Cloud: {galat_terakhir}"
    except Exception as exc:
        return False, "", f"Kesalahan inisialisasi klien Groq: {exc}"


def panggil_ollama_lokal(
    prompt: str,
    model_name: str = "qwen2.5:1.5b",
    base_url: str = "http://localhost:11434",
) -> tuple[bool, str, str]:
    """Panggil server Ollama lokal pada endpoint /api/generate."""
    url = f"{base_url.rstrip('/')}/api/generate"
    try:
        resp = requests.post(
            url,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4},
            },
            timeout=90,
        )
        if resp.status_code != 200:
            return (
                False,
                "",
                f"Ollama mengembalikan status {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()
        teks_keluaran = (data.get("response") or "").strip()
        teks_keluaran = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", teks_keluaran).strip()
        if not teks_keluaran:
            return False, "", "Respons Ollama kosong."
        return True, teks_keluaran, f"Ollama Lokal ({model_name})"
    except requests.exceptions.ConnectionError:
        return (
            False,
            "",
            f"Tidak dapat terhubung ke server Ollama di `{base_url}`. Pastikan `ollama serve` aktif dan model `{model_name}` sudah diunduh (`ollama pull {model_name}`).",
        )
    except Exception as exc:
        return False, "", f"Kesalahan saat menghubungi Ollama: {exc}"


def tombol_salin_clipboard(teks: str, key_id: str = "copy_btn") -> None:
    """Render tombol salin ke papan klip berbasis HTML/JS ringan."""
    teks_json = json.dumps(teks)
    html_code = f"""
    <div style="display:flex; align-items:center; gap:10px; margin-top:4px;">
        <button id="{key_id}" style="
            background-color:#0f172a;
            color:#ffffff;
            border:none;
            border-radius:6px;
            padding:7px 14px;
            font-size:0.85rem;
            font-weight:600;
            cursor:pointer;
            transition:background 0.2s;
        ">📋 Salin Hasil ke Clipboard</button>
        <span id="{key_id}_msg" style="font-size:0.82rem; color:#15803d; font-weight:600; display:none;">
            ✓ Tersalin!
        </span>
    </div>
    <script>
    const btn = document.getElementById("{key_id}");
    const msg = document.getElementById("{key_id}_msg");
    btn.addEventListener("click", () => {{
        const text = {teks_json};
        navigator.clipboard.writeText(text).then(() => {{
            msg.style.display = "inline";
            setTimeout(() => {{ msg.style.display = "none"; }}, 2200);
        }});
    }});
    </script>
    """
    components.html(html_code, height=44)


# ---------------------------------------------------------------------------
# Bilah Samping (Sidebar)
# ---------------------------------------------------------------------------
kamus_eyd_data = muat_kamus_eyd()
id_ai_tells_md = muat_id_ai_tells()

with st.sidebar:
    st.markdown("## ⚙️ Pengaturan & Kalibrasi")

    ambang_cv = st.slider(
        "Ambang Batas Toleransi CV (Koefisien Variasi)",
        min_value=0.20,
        max_value=0.80,
        value=0.45,
        step=0.05,
        help="Koefisien Variasi (SD / Rata-rata Kata) mengukur keragaman panjang kalimat (burstiness). Ambang standar tulisan manusia alami adalah >= 0.45.",
    )

    preset_register = st.selectbox(
        "Preset Register Ilmiah",
        options=["akademik", "ajar", "semiformal"],
        index=0,
        format_func=lambda x: {
            "akademik": "Akademik (Skripsi / Jurnal SINTA)",
            "ajar": "Buku Ajar / Modul",
            "semiformal": "Esai Ilmiah Semiformal",
        }[x],
    )

    st.markdown("### 🔍 Filter Sensitivitas Audit")
    cek_kaidah = st.checkbox(
        "Kaidah Wajib (K) — EYD V, KBBI, & Kata Depan",
        value=True,
        help="Pelanggaran ejaan EYD V, kata tidak baku KBBI, pemisahan 'di'/'ke', dan kalimat tanpa subjek.",
    )
    cek_gaya = st.checkbox(
        "Gaya Bahasa (G) — Keefektifan & Nominalisasi",
        value=True,
        help="Anjuran penyuntingan ilmiah: nominalisasi (melakukan pengukuran -> mengukur), kalimat >35 kata, dan kekuatan klaim.",
    )
    cek_ai = st.checkbox(
        "Pola AI (AI) — Klise, Trikolon, & Kalke",
        value=True,
        help="Frasa klise pembuka, trikolon, penyangkalan 'bukan X melainkan Y', dan kalke Inggris dari id-ai-tells.md.",
    )

    filter_aktif: list[str] = []
    if cek_kaidah:
        filter_aktif.append("K")
    if cek_gaya:
        filter_aktif.append("G")
    if cek_ai:
        filter_aktif.append("AI")

    with st.expander("🔑 Konfigurasi Koneksi Mesin (Opsional)"):
        router9_key_env = ambil_router9_api_key_awal()
        router9_api_key = st.text_input(
            "Router9 API Key",
            value=router9_key_env,
            type="password",
            key="router9_api_key_input",
            help="Diambil dari st.secrets['ROUTER9_API_KEY'] atau variabel lingkungan ROUTER9_API_KEY bila tersedia.",
        )
        groq_key_env = os.getenv("GROQ_API_KEY", "")
        groq_api_key = st.text_input(
            "Groq API Key",
            value=groq_key_env,
            type="password",
            help="Diambil otomatis dari berkas .env bila tersedia.",
        )
        ollama_url = st.text_input(
            "URL Ollama Lokal",
            value="http://localhost:11434",
        )
        ollama_model = st.text_input(
            "Model Ollama",
            value="qwen2.5:1.5b",
        )

    with st.expander("📖 Legenda Metrik & Panduan Singkat", expanded=False):
        st.markdown(
            """
            **1. Koefisien Variasi (CV) & Burstiness**
            - **Rumus:** `CV = Simpangan Baku / Rata-rata Kata`
            - **Target:** `CV ≥ 0.45` (dan Simpangan Baku `SD ≥ 6.4`).
            - Teks AI cenderung datar (`CV < 0.35`, semua kalimat 20–25 kata). Teks manusia memadukan kalimat pendek (4–7 kata) untuk temuan tegas dan kalimat panjang (20–28 kata) untuk penjelasan sebab-akibat.

            **2. Tingkat Kepadatan Kalimat**
            - Mengukur proporsi kalimat panjang (`≥ 28 kata`) dan kepadatan kata pemadat (`73–139 per 1.000 kata`).
            - Hindari memampatkan teks secara ekstrem maupun menumpuk klausa koordinatif (`koma + dan`).

            **3. Kode Warna Audit Linguistik**
            - 🔴 **[K] Kaidah Wajib:** Pelanggaran EYD V, kata tidak baku KBBI, awalan `di-` vs kata depan `di`, subjek hilang.
            - 🟡 **[AI] Pola AI:** Pembuka kosmik (*Di era digital*), trikolon (*efektif, efisien, dan...*), penyangkalan antisipatif (*bukan X, melainkan Y*), kalke (*yang mana*).
            - 🔵 **[G] Gaya Bahasa:** Nominalisasi berlebih (*melakukan pengukuran*), kalimat terlalu panjang (`> 35 kata`).

            **4. Kontrak Integritas Ilmiah**
            - Angka, satuan, nilai *p*, dan sitasi tidak boleh berubah maknanya saat perombakan ritme.
            """
        )

    st.caption(
        f"📚 Kamus aktif: **{len(periksa_eyd.KATA_BAKU) + len(kamus_eyd_data.get('kata_baku', {}))}** entri KBBI & EYD V"
    )

# ---------------------------------------------------------------------------
# Inisialisasi State Sesi
# ---------------------------------------------------------------------------
if "naskah_asli" not in st.session_state:
    st.session_state["naskah_asli"] = CONTOH_NASKAH
if "naskah_hasil" not in st.session_state:
    st.session_state["naskah_hasil"] = ""
if "mesin_terakhir" not in st.session_state:
    st.session_state["mesin_terakhir"] = ""

# ---------------------------------------------------------------------------
# Judul Utama Aplikasi
# ---------------------------------------------------------------------------
st.title("🎓 Skripsi Editor v2 — Audit EYD V & Penyelaras Ritme Ilmiah")
st.markdown(
    "Integrasi mesin **`core.metrik_ritme`** (*humanizer-indonesia*), **`core.periksa_eyd`** (*naskah-id*), "
    "dan **`core.sintaksis_semantik`** untuk mengaudit kaidah EYD V/KBBI, mendeteksi kolokasi & trikolon mesin, "
    "serta merombak ritme kalimat secara asimetris."
)

# ---------------------------------------------------------------------------
# Tata Letak Dua Kolom Utama
# ---------------------------------------------------------------------------
kol_kiri, kol_kanan = st.columns([1.05, 1.05], gap="large")

# ===========================================================================
# KOLOM KIRI: Input & Audit Naskah Asli
# ===========================================================================
with kol_kiri:
    st.subheader("📥 1. Input & Audit Naskah Asli")

    baris_tombol_kiri = st.columns([1, 1, 2])
    with baris_tombol_kiri[0]:
        if st.button("📄 Muat Contoh Uji", use_container_width=True):
            st.session_state["naskah_asli"] = CONTOH_NASKAH
            st.rerun()
    with baris_tombol_kiri[1]:
        if st.button("🗑️ Bersihkan Teks", use_container_width=True):
            st.session_state["naskah_asli"] = ""
            st.session_state["naskah_hasil"] = ""
            st.rerun()

    teks_input = st.text_area(
        "Masukkan draf paragraf atau bab skripsi:",
        key="naskah_asli",
        height=230,
        placeholder="Tempelkan draf latar belakang, tinjauan pustaka, metode, atau pembahasan skripsi Anda di sini...",
    )

    metrik_asli = analisis_ritme_lengkap(teks_input, preset=preset_register)
    temuan_asli = audit_naskah_lengkap(teks_input, kamus_eyd_data, filter_aktif)

    # --- Kartu Visual Metrik (CV, Rata-rata Kata, Tingkat Kepadatan Kalimat) ---
    st.markdown("#### 📊 Kartu Visual Metrik Ritme")
    if metrik_asli:
        c1, c2, c3 = st.columns(3)
        cv_val = metrik_asli["cv"]
        cv_lulus = cv_val >= ambang_cv
        badge_cv = (
            f'<span class="badge-ok">LULUS (≥ {ambang_cv:.2f})</span>'
            if cv_lulus
            else f'<span class="badge-err">DATAR (&lt; {ambang_cv:.2f})</span>'
        )

        rerata_val = metrik_asli["rerata"]
        lo_r, hi_r = metrik_asli["preset_target"]["rerata"]
        rerata_lulus = (lo_r <= rerata_val <= hi_r)
        badge_rerata = (
            f'<span class="badge-ok">Ideal ({lo_r:.0f}–{hi_r:.0f})</span>'
            if rerata_lulus
            else f'<span class="badge-warn">Rentang {lo_r:.0f}–{hi_r:.0f}</span>'
        )

        kepadatan_label = metrik_asli["label_kepadatan"]
        badge_padat = (
            '<span class="badge-ok">Seimbang</span>'
            if "Proporsional" in kepadatan_label
            else '<span class="badge-warn">Perlu Tinjau</span>'
        )

        with c1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Koefisien Variasi (CV)</div>
                    <div class="metric-value">{cv_val:.2f}</div>
                    <div class="metric-sub">{badge_cv} · SD: <b>{metrik_asli['sd']:.1f}</b> kata</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Rata-rata Kata / Kalimat</div>
                    <div class="metric-value">{rerata_val:.1f}</div>
                    <div class="metric-sub">{badge_rerata} · {metrik_asli['kalimat']} kal ({metrik_asli['kata']} kata)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Tingkat Kepadatan Kalimat</div>
                    <div class="metric-value" style="font-size:1.18rem;">{kepadatan_label}</div>
                    <div class="metric-sub">{badge_padat} · Pemadat: <b>{metrik_asli['pemadat']:.0f}</b>‰ · ≥28 kata: <b>{metrik_asli['panjang_pct']:.0f}%</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Masukkan minimal satu kalimat utuh untuk melihat metrik ritme naskah.")

    # --- Sorotan Visual Teks (Highlighting) ---
    st.markdown("#### 🖍️ Sorotan Visual Pelanggaran & Pola AI")
    st.caption(
        "Arahkan kursor pada kata yang disorot untuk melihat kode pelanggaran dan saran perbaikan: "
        "🔴 **Kaidah (K)** · 🟡 **Pola AI (AI)** · 🔵 **Gaya Bahasa (G)**"
    )
    html_sorot = sorot_teks_html(teks_input, temuan_asli)
    st.markdown(html_sorot, unsafe_allow_html=True)

    # --- Panel Tab / Expander Audit Linguistik ---
    st.markdown("#### 🔎 Panel Audit Linguistik")
    temuan_kaidah = [t for t in temuan_asli if t["label"] in ("K", "G")]
    temuan_ai = [t for t in temuan_asli if t["label"] == "AI"]

    tab_k, tab_ai, tab_ref = st.tabs(
        [
            f"📏 Tab Kaidah (K/G) ({len(temuan_kaidah)})",
            f"🤖 Tab Pola AI (AI) ({len(temuan_ai)})",
            "📚 Rujukan id-ai-tells.md",
        ]
    )

    with tab_k:
        if not temuan_kaidah:
            st.success("Tidak ditemukan pelanggaran kaidah EYD V atau kata tidak baku KBBI pada filter aktif.")
        else:
            for item in temuan_kaidah:
                kelas_css = f"audit-item-{item['label']}"
                label_teks = "Kaidah Wajib EYD V / KBBI" if item["label"] == "K" else "Anjuran Gaya Ilmiah"
                st.markdown(
                    f"""
                    <div class="audit-item {kelas_css}">
                        <b>[{item['kode']} · {label_teks}]</b> (Baris {item['baris']})<br/>
                        Cuplikan: <code>{html.escape(item['cuplikan'])}</code><br/>
                        💡 <b>Saran:</b> {html.escape(item['saran'])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with tab_ai:
        if not temuan_ai and (
            not metrik_asli
            or (
                metrik_asli["verba_ringan"] <= 0.40
                and metrik_asli["konektor"] <= 0.40
                and metrik_asli["sangkal"] == 0
            )
        ):
            st.success("Tidak ditemukan frasa klise AI, trikolon, atau penanda gaya mesin yang mencolok.")
        else:
            if metrik_asli:
                diag_cols = st.columns(3)
                diag_cols[0].metric(
                    "Verba Ringan / 100 kata",
                    f"{metrik_asli['verba_ringan']:.2f}",
                    delta="Target ≤ 0.40",
                    delta_color="normal" if metrik_asli["verba_ringan"] <= 0.40 else "inverse",
                )
                diag_cols[1].metric(
                    "Konektor / 100 kata",
                    f"{metrik_asli['konektor']:.2f}",
                    delta="Target ≤ 0.40",
                    delta_color="normal" if metrik_asli["konektor"] <= 0.40 else "inverse",
                )
                diag_cols[2].metric(
                    "Penyangkalan Antisipatif",
                    f"{metrik_asli['sangkal']}",
                    delta="Sasaran 0",
                    delta_color="normal" if metrik_asli["sangkal"] == 0 else "inverse",
                )

            for item in temuan_ai:
                st.markdown(
                    f"""
                    <div class="audit-item audit-item-AI">
                        <b>[{item['kode']} · Penanda Gaya Mesin]</b> (Baris {item['baris']})<br/>
                        Cuplikan: <code>{html.escape(item['cuplikan'])}</code><br/>
                        💡 <b>Saran:</b> {html.escape(item['saran'])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with tab_ref:
        st.caption("Katalog penanda AI Bahasa Indonesia dari `references/id-ai-tells.md`:")
        st.markdown(id_ai_tells_md[:4500] + ("\n\n..." if len(id_ai_tells_md) > 4500 else ""))


# ===========================================================================
# KOLOM KANAN: Hasil Perombakan & Penyelarasan
# ===========================================================================
with kol_kanan:
    st.subheader("✨ 2. Hasil Perombakan & Penyelarasan Ritme")

    opsi_mesin = [
        "Groq Cloud (Llama 3.3 70B - Super Cepat)",
        *ROUTER9_MODELS.keys(),
        "Ollama Lokal (Qwen 2.5 1.5B)",
        "Aturan Standar (Tanpa AI)",
    ]
    pilihan_mesin = st.selectbox(
        "Pilih Mesin Perombak Naskah:",
        options=opsi_mesin,
        index=0,
    )

    prompt_aktif = bangun_prompt_perombakan(
        teks=teks_input,
        metrik=metrik_asli,
        temuan=temuan_asli,
        target_cv=ambang_cv,
        preset=preset_register,
    )

    with st.expander("🛠️ Lihat Prompt Perombakan Ritme Asimetris (3–7 Kata & 20–28 Kata)"):
        st.code(prompt_aktif, language="markdown")

    tombol_rombak = st.button(
        "🚀 Jalankan Perombakan & Penyelarasan Ritme",
        type="primary",
        use_container_width=True,
        disabled=not bool(teks_input.strip()),
    )

    if tombol_rombak and teks_input.strip():
        if pilihan_mesin == "Groq Cloud (Llama 3.3 70B - Super Cepat)":
            with st.spinner("Menghubungi Groq Cloud (Llama 3.3 70B) untuk merombak ritme naskah..."):
                sukses, hasil_teks, info_mesin = panggil_groq_cloud(prompt_aktif, groq_api_key)
                if sukses:
                    st.session_state["naskah_hasil"] = hasil_teks
                    st.session_state["mesin_terakhir"] = info_mesin
                else:
                    st.warning(
                        f"{info_mesin}\n\nMengalihkan otomatis ke **Aturan Standar (Tanpa AI)** agar penyuntingan tetap berjalan."
                    )
                    st.session_state["naskah_hasil"] = rombak_aturan_standar(
                        teks_input, kamus_eyd_data, target_cv=ambang_cv
                    )
                    st.session_state["mesin_terakhir"] = "Aturan Standar (Fallback Lokal)"

        elif pilihan_mesin in ROUTER9_MODELS:
            model_id_r9 = ROUTER9_MODELS[pilihan_mesin]
            with st.spinner(f"Menghubungi {pilihan_mesin} (`{model_id_r9}`)..."):
                hasil_teks = panggil_router9(model_id_r9, prompt_aktif)
                if hasil_teks:
                    st.session_state["naskah_hasil"] = hasil_teks
                    st.session_state["mesin_terakhir"] = f"{pilihan_mesin} ({model_id_r9})"
                else:
                    st.info("Mengalihkan otomatis ke **Aturan Standar (Tanpa AI)** agar penyuntingan tetap berjalan.")
                    st.session_state["naskah_hasil"] = rombak_aturan_standar(
                        teks_input, kamus_eyd_data, target_cv=ambang_cv
                    )
                    st.session_state["mesin_terakhir"] = "Aturan Standar (Fallback Lokal)"

        elif pilihan_mesin == "Ollama Lokal (Qwen 2.5 1.5B)":
            with st.spinner(f"Menghubungi Ollama Lokal ({ollama_model})..."):
                sukses, hasil_teks, info_mesin = panggil_ollama_lokal(
                    prompt_aktif, model_name=ollama_model, base_url=ollama_url
                )
                if sukses:
                    st.session_state["naskah_hasil"] = hasil_teks
                    st.session_state["mesin_terakhir"] = info_mesin
                else:
                    st.warning(
                        f"{info_mesin}\n\nMengalihkan otomatis ke **Aturan Standar (Tanpa AI)**."
                    )
                    st.session_state["naskah_hasil"] = rombak_aturan_standar(
                        teks_input, kamus_eyd_data, target_cv=ambang_cv
                    )
                    st.session_state["mesin_terakhir"] = "Aturan Standar (Fallback Lokal)"

        else:
            with st.spinner("Menjalankan mesin Aturan Standar (Tanpa AI)..."):
                st.session_state["naskah_hasil"] = rombak_aturan_standar(
                    teks_input, kamus_eyd_data, target_cv=ambang_cv
                )
                st.session_state["mesin_terakhir"] = "Aturan Standar (Tanpa AI)"

    # Jika belum pernah dirombak namun ada teks contoh, tampilkan hasil awal Rule-Based agar metrik pembanding langsung terlihat
    if not st.session_state["naskah_hasil"] and teks_input.strip():
        st.session_state["naskah_hasil"] = rombak_aturan_standar(
            teks_input, kamus_eyd_data, target_cv=ambang_cv
        )
        st.session_state["mesin_terakhir"] = "Pratinjau Otomatis (Aturan Standar)"

    if st.session_state["mesin_terakhir"]:
        st.caption(f"✅ Mesin aktif terakhir: **{st.session_state['mesin_terakhir']}**")

    # --- Area Teks Hasil yang Dapat Disunting & Tombol Salin ---
    teks_hasil_sunting = st.text_area(
        "Area Teks Hasil Perombakan (Dapat Disunting Langsung):",
        key="naskah_hasil",
        height=230,
        help="Anda dapat menyunting langsung teks hasil ini. Grafik dan metrik pembanding di bawah akan otomatis diperbarui.",
    )

    kol_aksi_1, kol_aksi_2 = st.columns([1.3, 1])
    with kol_aksi_1:
        tombol_salin_clipboard(teks_hasil_sunting, key_id="salin_hasil_skripsi")
    with kol_aksi_2:
        st.download_button(
            label="💾 Unduh Hasil (.md)",
            data=teks_hasil_sunting.encode("utf-8"),
            file_name="naskah_skripsi_terselaraskan.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # --- Perbandingan Metrik Sebelum vs Sesudah & Grafik Sebaran Panjang Kalimat ---
    metrik_sesudah = analisis_ritme_lengkap(teks_hasil_sunting, preset=preset_register)
    temuan_sesudah = audit_naskah_lengkap(teks_hasil_sunting, kamus_eyd_data, filter_aktif)

    if metrik_asli and metrik_sesudah:
        st.markdown("#### 📈 Perbandingan Ritme & Kaidah (Sebelum vs Sesudah)")

        m1, m2, m3, m4 = st.columns(4)
        delta_cv = metrik_sesudah["cv"] - metrik_asli["cv"]
        delta_sd = metrik_sesudah["sd"] - metrik_asli["sd"]
        delta_temuan = len(temuan_sesudah) - len(temuan_asli)

        m1.metric(
            "Koefisien Variasi (CV)",
            f"{metrik_sesudah['cv']:.2f}",
            delta=f"{delta_cv:+.2f} vs asli",
            delta_color="normal",
        )
        m2.metric(
            "Burstiness (SD Kata)",
            f"{metrik_sesudah['sd']:.1f}",
            delta=f"{delta_sd:+.1f} kata",
            delta_color="normal",
        )
        m3.metric(
            "Rerata Kata / Kalimat",
            f"{metrik_sesudah['rerata']:.1f}",
            delta=f"{metrik_sesudah['rerata'] - metrik_asli['rerata']:+.1f} kata",
            delta_color="off",
        )
        m4.metric(
            "Temuan Audit (K/G/AI)",
            f"{len(temuan_sesudah)}",
            delta=f"{delta_temuan:+d} temuan",
            delta_color="inverse",
        )

        # Ringkasan Proporsi Kalimat Pendek (3-7 kata) & Panjang (20-28 kata)
        st.caption(
            f"🎯 **Distribusi Kalimat Hasil:** "
            f"Pendek (3–7 kata): **{metrik_sesudah['pendek_4_7']}** kalimat · "
            f"Panjang (20–28 kata): **{metrik_sesudah['panjang_20_28']}** kalimat · "
            f"Rentang: **{metrik_sesudah['terpendek']}–{metrik_sesudah['terpanjang']}** kata"
        )

        # --- Grafik Sebaran Panjang Kalimat (Altair) ---
        baris_data: list[dict[str, Any]] = []
        for idx, p in enumerate(metrik_asli["sebaran_kata"], start=1):
            baris_data.append(
                {
                    "Versi": "1. Sebelum (Asli)",
                    "Kalimat Ke": idx,
                    "Jumlah Kata": p,
                    "Cuplikan": metrik_asli["daftar_kalimat"][idx - 1][:70] + "...",
                }
            )
        for idx, p in enumerate(metrik_sesudah["sebaran_kata"], start=1):
            baris_data.append(
                {
                    "Versi": "2. Sesudah (Hasil)",
                    "Kalimat Ke": idx,
                    "Jumlah Kata": p,
                    "Cuplikan": metrik_sesudah["daftar_kalimat"][idx - 1][:70] + "...",
                }
            )

        df_sebaran = pd.DataFrame(baris_data)

        grafik_garis = (
            alt.Chart(df_sebaran)
            .mark_line(point=alt.OverlayMarkDef(size=70, filled=True), strokeWidth=2.5)
            .encode(
                x=alt.X("Kalimat Ke:O", title="Urutan Kalimat dalam Naskah"),
                y=alt.Y("Jumlah Kata:Q", title="Panjang Kalimat (Jumlah Kata)", scale=alt.Scale(zero=True)),
                color=alt.Color(
                    "Versi:N",
                    scale=alt.Scale(
                        domain=["1. Sebelum (Asli)", "2. Sesudah (Hasil)"],
                        range=["#ef4444", "#0f766e"],
                    ),
                    legend=alt.Legend(orient="top", title=None),
                ),
                tooltip=["Versi:N", "Kalimat Ke:O", "Jumlah Kata:Q", "Cuplikan:N"],
            )
            .properties(height=250)
        )

        # Garis referensi zona pendek (7 kata) dan panjang (20-28 kata)
        df_zona = pd.DataFrame(
            [
                {"batas": 7, "label": "Batas Kalimat Pendek (7 kata)"},
                {"batas": 20, "label": "Batas Bawah Kalimat Panjang (20 kata)"},
                {"batas": 28, "label": "Batas Atas Kalimat Panjang (28 kata)"},
            ]
        )
        garis_acuan = (
            alt.Chart(df_zona)
            .mark_rule(strokeDash=[4, 4], color="#94a3b8")
            .encode(y="batas:Q")
        )

        st.altair_chart(grafik_garis + garis_acuan, use_container_width=True)

        # --- Pemeriksaan Integritas Fakta Ilmiah (periksa_eyd.banding) ---
        laporan_fakta = periksa_eyd.banding(teks_input, teks_hasil_sunting)
        with st.expander(
            f"🛡️ Cek Integritas Angka, Sitasi, & Kutipan ({len(laporan_fakta)} catatan)",
            expanded=bool(laporan_fakta),
        ):
            if not laporan_fakta:
                st.success("Seluruh angka, sitasi, dan kutipan langsung terjaga utuh antara naskah asli dan hasil.")
            else:
                for jenis, ket in laporan_fakta:
                    if jenis == "PEMISAH":
                        st.info(f"**[{jenis}]** `{ket}` — Penyesuaian titik desimal menjadi koma sesuai EYD V.")
                    else:
                        st.warning(f"**[{jenis}]** `{ket}` — Pastikan tidak ada data penelitian yang berubah.")
