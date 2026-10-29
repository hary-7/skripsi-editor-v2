#!/usr/bin/env python3
"""
sintaksis_semantik.py - Modul Penguat Audit Sintaksis, Semantik, dan Anti-Pola AI
Melengkapi periksa_eyd.py dan metrik_ritme.py untuk deteksi karakteristik tulisan mesin.
"""

import re

# 1. KOLOKASI KLISE AKADEMIK & ADVERBIA KOSONG (EMPTY INTENSIFIERS)
KOLOKASI_KLISE = [
    (r"\bkontribusi\s+(?:yang\s+)?(?:signifikan|nyata|positif|substansial)\b", "kontribusi signifikan -> klise AI; sebutkan dampak konkretnya secara terukur"),
    (r"\blandasan\s+(?:yang\s+)?(?:fundamental|kokoh|krusial)\b", "landasan fundamental -> klise AI; ganti dengan dasar teoretis/pijakan acuan"),
    (r"\bpemahaman\s+(?:yang\s+)?(?:komprehensif|mendalam|holistik)\b", "pemahaman komprehensif -> ganti dengan batasan analisis yang jelas"),
    (r"\bperan\s+(?:yang\s+)?(?:krusial|vital|sentral|strategis)\b", "peran krusial -> sebutkan fungsi teknisnya secara spesifik"),
    (r"\bdinamika\s+(?:yang\s+)?(?:berkembang|kompleks)\b", "dinamika berkembang -> frasa hampa; fokus pada fenomena yang diamati"),
    (r"\btantangan\s+tersendiri\b", "tantangan tersendiri -> klise retorika; deskripsikan kendala lapangan sebenarnya"),
    (r"\blangkah\s+(?:yang\s+)?strategis\b", "langkah strategis -> sebutkan tindakan metodologisnya"),
    (r"\bimplikasi\s+(?:yang\s+)?luas\b", "implikasi luas -> nyatakan implikasi teoritis atau praktisnya"),
    (r"\bsecara\s+berkelanjutan\b", "secara berkelanjutan -> sering jadi penutup normatif AI"),
    (r"\bmemberikan\s+wawasan\s+(?:baru)?\b", "memberikan wawasan -> kalke give insights; pakai memperlihatkan/menunjukkan temuan"),
    # Adverbia Evaluatif Kosong
    (r"\bsecara\s+(?:holistik|komprehensif|substansial)\b", "adverbia evaluatif kosong khas AI; hapus dan biarkan bukti metodologis yang menjelaskan"),
    (r"\bsecara\s+(?:masif|eksponensial)\b", "klaim intensitas tanpa data kuantitatif; sebutkan persentase atau angka uji"),
    (r"\bsangat\s+optimal\b", "kata 'optimal' sudah menyatakan titik puncak; jangan gunakan penguat 'sangat'"),
]

# 2. KALKE RETORIS: SINDROM "TIDAK HANYA X, TETAPI JUGA Y"
POLA_KALKE_NOT_ONLY = re.compile(
    r"\b(?:tidak\s+hanya|bukan\s+hanya)\s+([^.,;]{3,50}),\s*(?:tetapi|melainkan)\s+(?:juga\s+)?([^.,;]{3,50})\b",
    re.IGNORECASE
)

# 3. ANTROPOMORFISME / PERSONIFIKASI BENDA MATI METODOLOGIS
POLA_ANTROPOMORFISME = re.compile(
    r"\b(?:penelitian|skripsi|kajian|tabel|grafik|data)\s+ini\s+(?:mencoba|berusaha|ingin|berharap)\s+(?:untuk\s+)?(?:memahami|mengungkap|membuktikan|menjelaskan)\b",
    re.IGNORECASE
)

# 4. PENUTUP PARAGRAF HARAPAN / KHOTBAH NORMATIF
POLA_PENUTUP_HARAPAN = re.compile(
    r"\b(?:diharapkan|perlu\s+adanya|langkah\s+ini\s+dapat\s+membawa)\s+[^.!?]+(?:kemajuan|manfaat|dampak\s+positif|masa\s+depan)\b",
    re.IGNORECASE
)

# 5. PENUMPUKAN MODALITAS EPISTEMIK (HEDGING BERTUMPUK)
HEDGING_BERTUMPUK = [
    (r"\b(?:tampaknya|sepertinya)\s+(?:dapat\s+dikatakan|dapat\s+disimpulkan)\b", "hedging ganda; langsung nyatakan hasil tanpa berputar"),
    (r"\bcenderung\s+(?:berpotensi|memiliki\s+kecenderungan)\b", "pleonasme modalitas: pilih salah satu ('cenderung' atau 'berpotensi')"),
    (r"\bdiduga\s+(?:kuat\s+)?(?:kemungkinan\s+besar)\b", "penumpukan dugaan; pakai 'diduga' atau nyatakan derajat signifikansinya"),
    (r"\bmungkin\s+dapat\s+diindikasikan\b", "modalitas berlebih; gunakan 'mengindikasikan' secara lugas"),
]

# 6. TRIKOLON KLAUSA & PREPOSISI
POLA_TRIKOLON_VERBA = re.compile(
    r"\b(me[a-z]{3,})\s+[^,;.]{4,40},\s+(me[a-z]{3,})\s+[^,;.]{4,40},\s+(?:dan|serta)\s+(me[a-z]{3,})\b",
    re.IGNORECASE
)
POLA_TRIKOLON_PREPOSISI = re.compile(
    r"\b(untuk|guna|demi)\s+[^,;.]{4,40},\s+(untuk|guna|demi)\s+[^,;.]{4,40},\s+(?:dan|serta)\s+(?:untuk|guna|demi)\b",
    re.IGNORECASE
)


def audit_sintaksis_semantik(teks):
    """
    Memindai naskah dan mengembalikan daftar temuan:
    Format: (nomor_baris, id_aturan, level, cuplikan, saran)
    """
    baris_list = teks.split("\n")
    hasil = []

    for idx, baris in enumerate(baris_list, start=1):
        if not baris.strip() or baris.strip().startswith(("#", "|", "<!--", "```")):
            continue

        # A. Kolokasi Klise AI & Adverbia Kosong
        for pola_str, saran in KOLOKASI_KLISE:
            for m in re.finditer(pola_str, baris, re.IGNORECASE):
                hasil.append((idx, "SEM-01", "AI", m.group(0), saran))

        # B. Kalke Retoris "Tidak hanya... tetapi juga..."
        for m in POLA_KALKE_NOT_ONLY.finditer(baris):
            hasil.append((
                idx, "SIN-04", "AI", m.group(0),
                "kalke kaku 'tidak hanya... tetapi juga...'; pecah kalimat atau gunakan konjungsi koordinatif tunggal"
            ))

        # C. Antropomorfisme Benda Mati
        for m in POLA_ANTROPOMORFISME.finditer(baris):
            hasil.append((
                idx, "SEM-03", "AI", m.group(0),
                "antropomorfisme metodologis (benda mati dianggap berkehendak); gunakan bentuk pasif objektif, misal: 'penelitian ini difokuskan pada...'"
            ))

        # D. Penutup Paragraf Bernada Harapan Normatif
        for m in POLA_PENUTUP_HARAPAN.finditer(baris):
            hasil.append((
                idx, "SEM-04", "AI", m.group(0),
                "penutup normatif klise AI; akhiri paragraf dengan data empiris, bukan kalimat harapan moralistik"
            ))

        # E. Hedging Bertumpuk
        for pola_str, saran in HEDGING_BERTUMPUK:
            for m in re.finditer(pola_str, baris, re.IGNORECASE):
                hasil.append((idx, "SEM-02", "AI", m.group(0), saran))

        # F. Trikolon Klausa & Preposisi
        for m in POLA_TRIKOLON_VERBA.finditer(baris):
            hasil.append((
                idx, "SIN-01", "AI", m.group(0),
                "trikolon klausa aktif (3 verba me- sejajar); ubah klausa ketiga menjadi kalimat terpisah"
            ))
        for m in POLA_TRIKOLON_PREPOSISI.finditer(baris):
            hasil.append((
                idx, "SIN-02", "AI", m.group(0),
                "trikolon preposisi tujuan berseri; pecah atau gabungkan gagasan secara asimetris"
            ))

        # G. Simetri Klausa (Ritme Metronomik) & Kegagalan Pelesapan Subjek
        kalimat_kalimat = [k.strip() for k in re.split(r"(?<=[.!?])\s+", baris) if len(k.strip().split()) >= 3]
        
        # Pengecekan simetri klausa internal
        for kal in kalimat_kalimat:
            klausa = [k.strip() for k in re.split(r",|;\s*", kal) if len(k.strip().split()) >= 4]
            if len(klausa) == 2:
                len1 = len(klausa[0].split())
                len2 = len(klausa[1].split())
                if len1 >= 8 and len2 >= 8 and abs(len1 - len2) <= 1:
                    hasil.append((
                        idx, "SIN-03", "AI", f"{klausa[0]} [,] {klausa[1]}",
                        f"simetri klausa mekanis ({len1} kata vs {len2} kata); gunakan variasi panjang asimetris atau kalimat inversi"
                    ))

        # Pengecekan kegagalan pelesapan subjek pada 2 kalimat berurutan
        for k_idx in range(len(kalimat_kalimat) - 1):
            k1 = kalimat_kalimat[k_idx]
            k2 = kalimat_kalimat[k_idx + 1]
            pola_subjek = r"^(?:Penelitian|Metode|Sistem|Pengujian|Kajian)\s+(?:ini|tersebut)"
            m1 = re.match(pola_subjek, k1, re.IGNORECASE)
            m2 = re.match(pola_subjek, k2, re.IGNORECASE)
            if m1 and m2:
                hasil.append((
                    idx, "SIN-05", "AI", f"{m1.group(0)} ... {m2.group(0)}",
                    "kegagalan pelesapan subjek; subjek pada kalimat kedua berulang kaku, lesapkan subjeknya secara alami atau gunakan kalimat pasif"
                ))

    return sorted(hasil, key=lambda x: x[0])


def buat_prompt_humanisasi_ketat(teks_asli):
    """
    Menghasilkan System Prompt anti-AI yang sangat ketat untuk model LLM
    dengan instruksi sintaksis asimetris dan penolakan pola prediktif.
    """
    prompt = f"""Anda adalah penyunting senior naskah akademik bahasa Indonesia. Tugas Anda adalah merombak teks berikut agar memiliki karakter tulisan manusia seutuhnya (lolos uji ritme AI dan bebas dari prediktabilitas leksikal).

Teks Asli:
\"\"\"
{teks_asli}
\"\"\"

Patuhi 6 aturan mutlak berikut:
1. RITME ASIMETRIS EKSTREM: Selingi kalimat panjang (22-30 kata) dengan kalimat deklaratif yang sangat pendek (3-6 kata) sebagai penegas temuan di tengah/akhir paragraf.
2. VARIASI SINTAKSIS & INVERSI: Jangan selalu menggunakan pola Subjek di awal kalimat. Gunakan kalimat inversi ilmiah (Predikat di depan) atau manfaatkan pelesapan subjek alami pada kalimat berikutnya.
3. BEBAS KLISE & TRIKOLON: Dilarang keras membuat daftar tiga kata/klausa berderet. Buang kata transisi klise seperti 'Selain itu', 'Dengan demikian', 'Di sisi lain', 'Oleh karena itu'.
4. LARANGAN KALKE & ANTROPOMORFISME: Hindari kalke 'tidak hanya X, tetapi juga Y'. Jangan mempersonifikasi dokumen ('penelitian ini berusaha memahami...'), melainkan gunakan bentuk pasif objektif ('penelitian ini difokuskan pada...').
5. LARANGAN PENUTUP HARAPAN: Dilarang mengakhiri paragraf dengan harapan moralistik ('Diharapkan dapat membawa dampak positif...'). Akhiri paragraf dengan simpulan data konkret.
6. INTEGRITAS DATA: Pertahankan 100% seluruh angka, nama dokumen resmi, sitasi nama penulis, dan tahun terbit secara presisi.

Tuliskan langsung teks hasil perombakan tanpa pengantar:"""
    return prompt
