import os
import sys
from pypdf import PdfReader
from db import save_user_knowledge, delete_old_knowledge
from ai_engine import get_embedding


def extract_text_from_pdf(pdf_path: str) -> str:
    """Mengekstrak teks dari file PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File PDF tidak ditemukan: {pdf_path}")

    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text.strip()


def process_and_save_knowledge(
    pdf_path: str, doc_type: str, title: str, asset_url: str = "local"
):
    """
    Pipeline Fase A: Ekstrak PDF -> Embedding -> Simpan ke Supabase.
    """
    print(f"📄 Memproses {doc_type}: {title}")

    # 1. Ekstrak Teks
    print("   [1/3] Mengekstrak teks dari PDF...")
    text_content = extract_text_from_pdf(pdf_path)
    if not text_content:
        raise ValueError(
            "Teks yang diekstrak dari PDF kosong. Mungkin PDF tersebut berupa gambar (scan) tanpa OCR."
        )
    print(f"   ✅ Teks berhasil diekstrak ({len(text_content)} karakter).")

    # 2. Generate Embedding
    print("   [2/3] Menghasilkan vector embedding (Gemini)...")
    # Batasi teks maksimal ~15.000 karakter agar aman dari limit token free tier & proses lebih cepat
    safe_text = text_content[:15000]
    embedding = get_embedding(safe_text)
    print(f"   ✅ Embedding berhasil (Dimensi: {len(embedding)}).")

    # 3. Simpan ke Supabase (hapus versi lama doc_type yang sama dulu, jaga storage free tier)
    print("   [3/3] Menyimpan ke database Supabase...")
    delete_old_knowledge(doc_type)
    result = save_user_knowledge(
        type=doc_type,
        title=title,
        text_content=safe_text,
        embedding=embedding,
        asset_url=asset_url,
    )
    print(f"   ✅ Berhasil disimpan! ID Database: {result['id']}")
    return result


if __name__ == "__main__":
    # Pemakaian:
    #   python knowledge_builder.py                                      -> isi profil utama (default di bawah)
    #   python knowledge_builder.py resume.pdf profile "Judul Bebas"      -> isi/replace profil utama
    #   python knowledge_builder.py proyek_alien.pdf project_doc "ALIEN"  -> tambah dokumen proyek terpisah
    #
    # CATATAN (v3): ingest.py TIDAK lagi memakai user_knowledge sebagai acuan
    # similarity filter — acuan itu sekarang profile_text tiap bidang di tracks.py.
    # type="profile" = resume lengkap terbaru; type="project_doc" = satu dokumen
    # per proyek (ALIEN, Orion, dst). Semuanya dipakai main.py sebagai konteks RAG
    # tambahan saat deep reasoning.
    target_pdf = sys.argv[1] if len(sys.argv) > 1 else "profile.pdf"
    doc_type = sys.argv[2] if len(sys.argv) > 2 else "profile"
    title = (
        sys.argv[3]
        if len(sys.argv) > 3
        else "Orie Grenitho - AI Solutions & Automation Developer"
    )

    if not os.path.exists(target_pdf):
        print(f"⚠️ File '{target_pdf}' tidak ditemukan di folder ini.")
        print(f"👉 Salin resume kamu ke folder ini dengan nama '{target_pdf}',")
        print(
            "   atau jalankan: python knowledge_builder.py <path_pdf> <doc_type> <judul>"
        )
        sys.exit(1)

    print("\n🚀 Memulai Fase A: Knowledge Builder...")
    try:
        process_and_save_knowledge(
            pdf_path=target_pdf,
            doc_type=doc_type,
            title=title,
            asset_url="local_file",
        )
        print(f"\n🎉 Fase A Selesai! '{doc_type}' tersimpan sebagai '{title}'.")
        if doc_type == "profile":
            print(
                "   -> Dokumen type='profile' = konteks utama juri AI di main.py. "
                "(Sejak v3, acuan similarity filter ada di tracks.py, bukan di sini.)"
            )
    except Exception as e:
        print(f"\n❌ Gagal memproses: {e}")
