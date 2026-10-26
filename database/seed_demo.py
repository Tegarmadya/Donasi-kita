"""
Seed Demo Data Script for DonasiKita.
Initializes database schema and populates realistic Indonesian demo data
for college UTS evaluation and live demonstration.
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import bcrypt

# Ensure root folder is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db


def hash_password(plain_password: str) -> str:
    """Hashes password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')


def run_schema():
    """Reads schema.sql and executes table creation."""
    schema_path = config.DATABASE_DIR / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    print("[INFO] Executing schema.sql...")
    db.execute_script(schema_sql)
    print("[SUCCESS] Database schema initialized.")


def seed_data():
    """Populates realistic demo data."""
    print("[INFO] Seeding demo data...")
    password_hash = hash_password("password123")
    
    # -------------------------------------------------------------------------
    # 1. Users
    # -------------------------------------------------------------------------
    users = [
        # Admin
        ("Administrator DonasiKita", "admin@donasikita.id", password_hash, "admin", "081234567890", "avatar_admin.png"),
        # Fundraisers
        ("Yayasan Lentera Harapan", "lentera@donasikita.id", password_hash, "fundraiser", "081298765432", "avatar_fundraiser1.png"),
        ("Relawan Nusantara Peduli", "relawan@donasikita.id", password_hash, "fundraiser", "081345678901", "avatar_fundraiser2.png"),
        ("Komunitas Guru Pesisir", "guru@donasikita.id", password_hash, "fundraiser", "081399887766", "avatar_fundraiser3.png"),
        # Donors
        ("Budi Santoso", "budi@donasikita.id", password_hash, "donatur", "085611223344", "avatar_donor1.png"),
        ("Siti Aminah", "siti@donasikita.id", password_hash, "donatur", "085722334455", "avatar_donor2.png"),
        ("Ahmad Fauzi", "ahmad@donasikita.id", password_hash, "donatur", "085833445566", "avatar_donor3.png"),
        ("Rina Wijaya", "rina@donasikita.id", password_hash, "donatur", "081944556677", "avatar_donor4.png"),
    ]
    
    user_ids = {}
    for full_name, email, p_hash, role, phone, avatar in users:
        sql = """
            INSERT INTO users (full_name, email, password_hash, role, phone, avatar, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'active')
        """
        res = db.execute_query(sql, (full_name, email, p_hash, role, phone, avatar), commit=True)
        user_ids[email] = res["last_insert_id"]
    print(f"[OK] Seeded {len(users)} users.")

    # -------------------------------------------------------------------------
    # 2. Categories
    # -------------------------------------------------------------------------
    categories = [
        ("Medis & Kesehatan", "medis-kesehatan", "Bantuan biaya pengobatan, operasi, dan perawatan medis dhuafa.", "activity"),
        ("Tanggap Bencana", "tanggap-bencana", "Bantuan darurat logistik, hunian sementara, dan pemulihan pasca bencana.", "shield-alert"),
        ("Pendidikan", "pendidikan", "Beasiswa, perlengkapan sekolah, dan renovasi ruang kelas pelosok.", "book-open"),
        ("Panti Asuhan & Yatim", "panti-asuhan-yatim", "Kebutuhan pokok, nutrisi, dan pembinaan anak-anak yatim piatu.", "heart"),
        ("Sarana Ibadah", "sarana-ibadah", "Pembangunan dan renovasi masjid, musholla, serta sarana umum.", "home"),
        ("Sosial & Kemanusiaan", "sosial-kemanusiaan", "Pemberdayaan ekonomi dhuafa dan bantuan kemanusiaan terpadu.", "users"),
    ]
    
    category_ids = {}
    for name, slug, desc, icon in categories:
        sql = """
            INSERT INTO categories (name, slug, description, icon, is_active)
            VALUES (%s, %s, %s, %s, 1)
        """
        res = db.execute_query(sql, (name, slug, desc, icon), commit=True)
        category_ids[slug] = res["last_insert_id"]
    print(f"[OK] Seeded {len(categories)} categories.")

    # -------------------------------------------------------------------------
    # 3. Campaigns
    # -------------------------------------------------------------------------
    today = date.today()
    campaigns = [
        {
            "user_email": "lentera@donasikita.id",
            "category_slug": "medis-kesehatan",
            "title": "Bantu Dek Rayyan Berjuang Melawan Leukemia Limfoblastik Akut",
            "slug": "bantu-dek-rayyan-berjuang-leukemia",
            "short_desc": "Rayyan (4 tahun) membutuhkan protokol kemoterapi intensif dan obat penunjang yang tidak ditanggung BPJS.",
            "story": """Dek Rayyan adalah balita berusia 4 tahun asal Sleman, Yogyakarta yang periang dan aktif. Tiga bulan lalu, keceriaan Rayyan mendadak pudar saat demam tinggi berkepanjangan tak kunjung reda disertai lebam di sekujur tubuhnya.

Setelah menjalani serangkaian tes sumsum tulang belakang di RSUP Sardjito, dokter mendiagnosis Rayyan menderita Leukemia Limfoblastik Akut (ALL). Rayyan harus menjalani 110 siklus protokol kemoterapi selama 2 tahun ke depan.

Ayah Rayyan bekerja sebagai buruh bengkel harian dengan penghasilan Rp 50.000/hari, sedangkan Ibu merawat Rayyan penuh waktu di rumah sakit. Beberapa obat penunjang kekebalan tubuh, nutrisi medis khusus, serta biaya operasional rujukan antar kota tidak seluruhnya ditanggung BPJS.

Mari bersama kita ulurkan tangan menjadi lentera harapan bagi kesembuhan Dek Rayyan agar ia bisa kembali tersenyum dan bermain bersama teman-temannya.""",
            "target": 85000000.00,
            "deadline": today + timedelta(days=45),
            "image": "campaign_rayyan.jpg",
            "status": "active"
        },
        {
            "user_email": "relawan@donasikita.id",
            "category_slug": "panti-asuhan-yatim",
            "title": "Sedekah Pangan & Gizi Sehat untuk 150 Santri Yatim Penghafal Al-Qur'an",
            "slug": "sedekah-pangan-gizi-150-santri-yatim",
            "short_desc": "Penuhi kebutuhan beras, lauk berprotein, dan susu bergizi untuk anak-anak yatim di Pesantren Nurul Huda.",
            "story": """Pesantren Nurul Huda menaungi 150 santri yatim dan dhuafa dari berbagai pelosok nusantara. Mereka belajar dan menghafal Al-Qur'an secara gratis tanpa dipungut biaya sepeser pun.

Setiap bulan, pesantren membutuhkan sedikitnya 1,5 ton beras, 300 kg telur dan daging, serta suplemen vitamin agar anak-anak tetap sehat dan bertenaga saat menghafal kitab suci. Kenaikan harga bahan pokok baru-baru ini membuat persediaan dapur umum sering kali menipis.

Melalui program Sedekah Pangan ini, kami mengajak Sahabat DonasiKita untuk patungan menyediakan paket gizi lengkap yang akan disalurkan setiap pekan selama masa pembinaan.""",
            "target": 45000000.00,
            "deadline": today + timedelta(days=30),
            "image": "campaign_santri.jpg",
            "status": "active"
        },
        {
            "user_email": "guru@donasikita.id",
            "category_slug": "pendidikan",
            "title": "Renovasi Jembatan Penyeberangan & Akses Belajar Siswa SDN 03 Pelosok",
            "slug": "renovasi-jembatan-sekolah-sdn03",
            "short_desc": "Setiap hari 80 murid harus menyeberangi jembatan bambu rapuh di atas sungai berarus deras demi bersekolah.",
            "story": """Di Desa Sukamaju, jembatan bambu sepanjang 35 meter menjadi satu-satunya akses anak-anak untuk pergi ke sekolah. Setiap musim penghujan tiba, debit air sungai meluap dan membuat jembatan bambu bergoyang licin serta rawan runtuh.

Tahun lalu, dua orang siswa tergelincir ke sungai dan buku-buku pelajarannya hanyut. Para orang tua cemas melepaskan anak-anak mereka menuntut ilmu.

Rencana renovasi ini akan membangun jembatan gantung berpondasi beton dan sling baja kokoh, dilengkapi pagar pengaman setinggi 1,2 meter agar siswa dan warga desa dapat melintas dengan tenang dan selamat sepanjang tahun.""",
            "target": 60000000.00,
            "deadline": today + timedelta(days=60),
            "image": "campaign_jembatan.jpg",
            "status": "active"
        },
        {
            "user_email": "relawan@donasikita.id",
            "category_slug": "tanggap-bencana",
            "title": "Bantuan Tanggap Darurat Banjir Bandang dan Dapur Umum Pesisir",
            "slug": "tanggap-darurat-banjir-bandang-pesisir",
            "short_desc": "Lebih dari 400 keluarga mengungsi akibat banjir bandang. Membutuhkan selimut, obat, dan makanan siap santap.",
            "story": """Hujan ekstrem selama tiga hari berturut-turut mengakibatkan tanggul sungai jebol dan menenggelamkan permukiman warga hingga ketinggian 1,8 meter di kawasan pesisir.

Ratusan keluarga kini mengungsi di balai desa dengan perlengkapan seadanya. Kebutuhan mendesak saat ini adalah pendirian posko dapur umum terpadu, penyediaan alas tidur, selimut hangat, popok bayi, air mineral higienis, dan obat-obatan penyakit kulit.""",
            "target": 50000000.00,
            "deadline": today + timedelta(days=12),
            "image": "campaign_banjir.jpg",
            "status": "active"
        },
        {
            "user_email": "lentera@donasikita.id",
            "category_slug": "sarana-ibadah",
            "title": "Pembangunan Sumur Bor Air Bersih & MCK Sehat Dusun Karang Rejo",
            "slug": "pembangunan-sumur-bor-karang-rejo",
            "short_desc": "Membantu 300 warga yang mengalami krisis air bersih berkepanjangan saat musim kemarau.",
            "story": """Warga Dusun Karang Rejo harus berjalan kaki sejauh 2 kilometer menuruni lereng bukit curam hanya untuk mengambil dua jeriken air keruh dari mata air resapan kecil.

Campaign ini ditujukan untuk pengeboran sumur air dalam (kedalaman 70 meter), instalasi pompa submersible tenaga surya, serta pembangunan bak penampung toren dan sanitasi MCK umum di dekat musholla dusun.

Status: Menunggu persetujuan tim kurasi admin DonasiKita untuk memverifikasi dokumen RAB teknis lapangan.""",
            "target": 35000000.00,
            "deadline": today + timedelta(days=50),
            "image": "campaign_sumur.jpg",
            "status": "pending"  # Demo for Admin approval!
        },
        {
            "user_email": "guru@donasikita.id",
            "category_slug": "sosial-kemanusiaan",
            "title": "Bantuan Modal Usaha Gerobak Berkah untuk 20 Ibu Tangguh Single Parent",
            "slug": "modal-usaha-gerobak-berkah-ibu-tangguh",
            "short_desc": "Pemberdayaan ekonomi mandiri bagi ibu-ibu kepala keluarga dhuafa agar terbebas dari jerat rentenir.",
            "story": """Program pendampingan wirausaha mikro berupa pemberian gerobak jualan kuliner higienis, modal bahan baku awal, serta pelatihan pembukuan sederhana untuk ibu-ibu pejuang nafkah.""",
            "target": 30000000.00,
            "deadline": today + timedelta(days=40),
            "image": "campaign_gerobak.jpg",
            "status": "active"
        },
        {
            "user_email": "relawan@donasikita.id",
            "category_slug": "medis-kesehatan",
            "title": "Operasi Katarak Gratis untuk 50 Lansia Dhuafa Daerah Terpencil",
            "slug": "operasi-katarak-gratis-50-lansia",
            "short_desc": "Mengembalikan penglihatan dan senyum para kakek-nenek dhuafa yang bertahun-tahun hidup dalam kegelapan.",
            "story": """Alhamdulillah, program operasi katarak massal bekerja sama dengan klinik spesialis mata telah selesai dilaksanakan dengan sukses. 52 lansia telah berhasil dioperasi dan pulih sempurna.""",
            "target": 40000000.00,
            "deadline": today - timedelta(days=5),
            "image": "campaign_katarak.jpg",
            "status": "completed"
        },
        {
            "user_email": "lentera@donasikita.id",
            "category_slug": "sosial-kemanusiaan",
            "title": "Bantuan Usaha Pribadi Pembelian Sepeda Motor Baru",
            "slug": "bantuan-usaha-pribadi-motor",
            "short_desc": "Pengajuan dana bantuan modal beli kendaraan pribadi.",
            "story": """Pengajuan tidak memenuhi syarat kelayakan sosial dan ditolak saat tahap kurasi admin.""",
            "target": 18000000.00,
            "deadline": today + timedelta(days=20),
            "image": "campaign_default.jpg",
            "status": "rejected"
        }
    ]

    campaign_ids = {}
    for camp in campaigns:
        sql = """
            INSERT INTO campaigns (
                user_id, category_id, title, slug, short_description, story,
                target_amount, collected_amount, deadline_date, image_url, status, rejection_reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0.00, %s, %s, %s, %s)
        """
        rej_reason = "Pengajuan tidak memenuhi standar verifikasi sosial kemanusiaan DonasiKita." if camp["status"] == "rejected" else None
        res = db.execute_query(sql, (
            user_ids[camp["user_email"]],
            category_ids[camp["category_slug"]],
            camp["title"],
            camp["slug"],
            camp["short_desc"],
            camp["story"],
            camp["target"],
            camp["deadline"],
            camp["image"],
            camp["status"],
            rej_reason
        ), commit=True)
        campaign_ids[camp["slug"]] = res["last_insert_id"]
    print(f"[OK] Seeded {len(campaigns)} campaigns.")

    # -------------------------------------------------------------------------
    # 4. Realistic Donations & Payments
    # -------------------------------------------------------------------------
    donations_data = [
        # Campaign 1: Rayyan (Target 85jt, realistic seed donations)
        {
            "campaign_slug": "bantu-dek-rayyan-berjuang-leukemia",
            "donor_email": "budi@donasikita.id",
            "donor_name": "Budi Santoso",
            "amount": 2500000.00,
            "is_anonymous": 0,
            "prayer": "Semoga Dek Rayyan lekas sembuh, diberikan kekuatan untuk keluarga. Aamiin.",
            "status": "success",
            "method": "bank_transfer",
            "channel": "BCA Virtual Account",
            "days_ago": 8
        },
        {
            "campaign_slug": "bantu-dek-rayyan-berjuang-leukemia",
            "donor_email": "siti@donasikita.id",
            "donor_name": "Siti Aminah",
            "amount": 1000000.00,
            "is_anonymous": 0,
            "prayer": "Syafakallah Dek Rayyan ganteng, semangat berobat ya nak.",
            "status": "success",
            "method": "qris",
            "channel": "QRIS Dinamis",
            "days_ago": 6
        },
        {
            "campaign_slug": "bantu-dek-rayyan-berjuang-leukemia",
            "donor_email": "ahmad@donasikita.id",
            "donor_name": "Ahmad Fauzi",
            "amount": 500000.00,
            "is_anonymous": 1,  # Anonymous donor
            "prayer": "Semoga berkah dan meringankan beban pengobatan.",
            "status": "success",
            "method": "ewallet",
            "channel": "GoPay",
            "days_ago": 4
        },
        {
            "campaign_slug": "bantu-dek-rayyan-berjuang-leukemia",
            "donor_email": "rina@donasikita.id",
            "donor_name": "Rina Wijaya",
            "amount": 1500000.00,
            "is_anonymous": 0,
            "prayer": "Bismillah, lekas pulih ya Rayyan sayang.",
            "status": "success",
            "method": "bank_transfer",
            "channel": "Mandiri Livin",
            "days_ago": 2
        },
        {
            "campaign_slug": "bantu-dek-rayyan-berjuang-leukemia",
            "donor_email": "budi@donasikita.id",
            "donor_name": "Budi Santoso",
            "amount": 750000.00,
            "is_anonymous": 0,
            "prayer": "Tambahan doa dari keluarga di Surabaya.",
            "status": "success",
            "method": "qris",
            "channel": "QRIS Dinamis",
            "days_ago": 1
        },
        # Pending donation for Campaign 1
        {
            "campaign_slug": "bantu-dek-rayyan-berjuang-leukemia",
            "donor_email": "rina@donasikita.id",
            "donor_name": "Rina Wijaya",
            "amount": 300000.00,
            "is_anonymous": 0,
            "prayer": "Sedang menunggu transfer.",
            "status": "pending",
            "method": "bank_transfer",
            "channel": "BRI Virtual Account",
            "days_ago": 0
        },

        # Campaign 2: Santri Yatim (Target 45jt)
        {
            "campaign_slug": "sedekah-pangan-gizi-150-santri-yatim",
            "donor_email": "siti@donasikita.id",
            "donor_name": "Siti Aminah",
            "amount": 3000000.00,
            "is_anonymous": 0,
            "prayer": "Semoga adik-adik santri istiqomah menghafal Al-Qur'an dan menjadi anak sholeh.",
            "status": "success",
            "method": "bank_transfer",
            "channel": "BNI Virtual Account",
            "days_ago": 10
        },
        {
            "campaign_slug": "sedekah-pangan-gizi-150-santri-yatim",
            "donor_email": "ahmad@donasikita.id",
            "donor_name": "Ahmad Fauzi",
            "amount": 2000000.00,
            "is_anonymous": 0,
            "prayer": "Pahala untuk kedua orang tua kami di alam barzakh.",
            "status": "success",
            "method": "ewallet",
            "channel": "OVO Cash",
            "days_ago": 5
        },
        {
            "campaign_slug": "sedekah-pangan-gizi-150-santri-yatim",
            "donor_email": "budi@donasikita.id",
            "donor_name": "Budi Santoso",
            "amount": 1000000.00,
            "is_anonymous": 1,
            "prayer": "Semoga berkah melimpah untuk santri dan pengasuh.",
            "status": "success",
            "method": "qris",
            "channel": "QRIS Dinamis",
            "days_ago": 3
        },

        # Campaign 3: Jembatan Sekolah
        {
            "campaign_slug": "renovasi-jembatan-sekolah-sdn03",
            "donor_email": "ahmad@donasikita.id",
            "donor_name": "Ahmad Fauzi",
            "amount": 5000000.00,
            "is_anonymous": 0,
            "prayer": "Semoga jembatan segera kokoh dan anak-anak bisa belajar dengan aman.",
            "status": "success",
            "method": "bank_transfer",
            "channel": "BCA Virtual Account",
            "days_ago": 7
        },
        {
            "campaign_slug": "renovasi-jembatan-sekolah-sdn03",
            "donor_email": "rina@donasikita.id",
            "donor_name": "Rina Wijaya",
            "amount": 2500000.00,
            "is_anonymous": 0,
            "prayer": "Terus maju pendidikan pelosok Indonesia!",
            "status": "success",
            "method": "bank_transfer",
            "channel": "Mandiri Livin",
            "days_ago": 4
        },

        # Campaign 4: Tanggap Darurat Banjir
        {
            "campaign_slug": "tanggap-darurat-banjir-bandang-pesisir",
            "donor_email": "budi@donasikita.id",
            "donor_name": "Budi Santoso",
            "amount": 4000000.00,
            "is_anonymous": 0,
            "prayer": "Bantuan darurat dapur umum. Semoga banjir lekas surut.",
            "status": "success",
            "method": "qris",
            "channel": "QRIS Dinamis",
            "days_ago": 2
        },
        {
            "campaign_slug": "tanggap-darurat-banjir-bandang-pesisir",
            "donor_email": "siti@donasikita.id",
            "donor_name": "Siti Aminah",
            "amount": 1500000.00,
            "is_anonymous": 1,
            "prayer": "Kuatkan saudara-saudara kita yang terkena musibah.",
            "status": "success",
            "method": "ewallet",
            "channel": "Dana",
            "days_ago": 1
        },

        # Failed donation example (shows realistic failure state)
        {
            "campaign_slug": "bantu-dek-rayyan-berjuang-leukemia",
            "donor_email": "ahmad@donasikita.id",
            "donor_name": "Ahmad Fauzi",
            "amount": 200000.00,
            "is_anonymous": 0,
            "prayer": "Percobaan simulasi gagal saldo tidak mencukupi.",
            "status": "failed",
            "method": "ewallet",
            "channel": "GoPay",
            "days_ago": 1
        },

        # Completed campaign donations (Operasi katarak reached 41.5jt)
        {
            "campaign_slug": "operasi-katarak-gratis-50-lansia",
            "donor_email": "budi@donasikita.id",
            "donor_name": "Budi Santoso",
            "amount": 20000000.00,
            "is_anonymous": 0,
            "prayer": "Wakaf produktif untuk kesehatan mata para lansia dhuafa.",
            "status": "success",
            "method": "bank_transfer",
            "channel": "BCA Virtual Account",
            "days_ago": 20
        },
        {
            "campaign_slug": "operasi-katarak-gratis-50-lansia",
            "donor_email": "siti@donasikita.id",
            "donor_name": "Siti Aminah",
            "amount": 21500000.00,
            "is_anonymous": 0,
            "prayer": "Alhamdulillah semoga bermanfaat.",
            "status": "success",
            "method": "bank_transfer",
            "channel": "Mandiri Livin",
            "days_ago": 18
        }
    ]

    don_counter = 1000
    for don in donations_data:
        don_counter += 1
        camp_id = campaign_ids[don["campaign_slug"]]
        user_id = user_ids[don["donor_email"]]
        don_code = f"DON-{datetime.now().strftime('%Y%m')}-{don_counter}"
        pay_code = f"PAY-{datetime.now().strftime('%Y%m')}-{don_counter}"
        don_time = datetime.now() - timedelta(days=don["days_ago"], hours=2)
        
        # Insert Donation
        sql_don = """
            INSERT INTO donations (
                donation_code, campaign_id, user_id, donor_name, donor_email,
                amount, is_anonymous, prayer_message, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        res_don = db.execute_query(sql_don, (
            don_code,
            camp_id,
            user_id,
            don["donor_name"],
            don["donor_email"],
            don["amount"],
            don["is_anonymous"],
            don["prayer"],
            don["status"],
            don_time,
            don_time
        ), commit=True)
        donation_id = res_don["last_insert_id"]

        # Insert Payment
        pay_status = don["status"]
        paid_at = don_time if pay_status == "success" else None
        ref_no = f"SIM-REF-{don_counter}"
        instructions = f"Silakan transfer ke nomor virtual account / scan QRIS resmi simulasi DonasiKita."
        
        sql_pay = """
            INSERT INTO payments (
                payment_code, donation_id, payment_method, payment_channel,
                payment_status, payment_reference, instructions, paid_at, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(sql_pay, (
            pay_code,
            donation_id,
            don["method"],
            don["channel"],
            pay_status,
            ref_no,
            instructions,
            paid_at,
            don_time
        ), commit=True)

        # If success, update campaign's collected_amount
        if pay_status == "success":
            sql_upd = """
                UPDATE campaigns
                SET collected_amount = collected_amount + %s
                WHERE id = %s
            """
            db.execute_query(sql_upd, (don["amount"], camp_id), commit=True)

            # Issue Certificate
            cert_no = f"DK-CERT/{datetime.now().strftime('%Y%m')}/{don_counter}"
            display_name = "Hamba Allah" if don["is_anonymous"] else don["donor_name"]
            camp_info = db.execute_query("SELECT title FROM campaigns WHERE id = %s", (camp_id,), fetch_one=True)
            v_code = f"VERIF-{don_code}-{don_counter}"
            
            sql_cert = """
                INSERT INTO certificates (
                    certificate_number, donation_id, donor_name_display,
                    campaign_title, amount, issue_date, verification_code, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute_query(sql_cert, (
                cert_no,
                donation_id,
                display_name,
                camp_info["title"],
                don["amount"],
                don_time.date(),
                v_code,
                don_time
            ), commit=True)

    print(f"[OK] Seeded {len(donations_data)} donations with matching payments and certificates.")

    # -------------------------------------------------------------------------
    # 5. Campaign Updates
    # -------------------------------------------------------------------------
    rayyan_id = campaign_ids["bantu-dek-rayyan-berjuang-leukemia"]
    santri_id = campaign_ids["sedekah-pangan-gizi-150-santri-yatim"]
    jembatan_id = campaign_ids["renovasi-jembatan-sekolah-sdn03"]

    updates = [
        (
            rayyan_id,
            "Hasil Pemeriksaan Darah Lengkap & Siklus Kemo ke-2",
            "Alhamdulillah, kondisi kadar hemoglobin Dek Rayyan menunjukkan perbaikan pasca transfusi dua kantong sel darah merah. Dokter spesialis onkologi anak telah menjadwalkan siklus kemoterapi kedua pekan ini. Terima kasih kepada seluruh Sahabat DonasiKita atas doa dan donasi yang terus mengalir.",
            "update_rayyan_1.jpg"
        ),
        (
            rayyan_id,
            "Penyaluran Bantuan Nutrisi & Obat Pendamping",
            "Tim relawan telah menyerahkan bantuan tahap pertama senilai Rp 3.500.000 untuk pembelian susu khusus penunjang berat badan medis dan obat anti-mual yang tidak masuk plafon BPJS.",
            "update_rayyan_2.jpg"
        ),
        (
            santri_id,
            "Penyaluran 500 Kg Beras & Minyak Goreng Tahap 1",
            "Bahan pokok kebutuhan dapur santri Nurul Huda telah didistribusikan langsung ke gudang logistik pesantren. Wajah ceria para santri menyambut kedatangan beras kualitas prima dan lauk pauk bergizi.",
            "update_santri_1.jpg"
        ),
        (
            jembatan_id,
            "Kedatangan Material Besi WF & Tiang Pancang",
            "Material rangka baja jembatan gantung SDN 03 telah sampai di balai pertemuan desa. Warga bergotong-royong mengangkut material ke pinggir sungai untuk persiapan pengecoran pondasi angkur.",
            "update_jembatan_1.jpg"
        )
    ]
    for c_id, title, content, img in updates:
        sql_u = """
            INSERT INTO campaign_updates (campaign_id, title, content, image_url)
            VALUES (%s, %s, %s, %s)
        """
        db.execute_query(sql_u, (c_id, title, content, img), commit=True)
    print(f"[OK] Seeded {len(updates)} campaign updates.")

    # -------------------------------------------------------------------------
    # 6. Fund Usage Reports (Transparansi Penggunaan Dana)
    # -------------------------------------------------------------------------
    fund_usages = [
        (
            rayyan_id,
            "Pembelian Obat Khusus Kemo & Nutrisi Formula Tinggi",
            "Medis & Farmasi",
            3500000.00,
            today - timedelta(days=5),
            "Penebusan resep obat anti-emetik injeksi, antibiotik profilaksis, dan 4 kaleng susu medis khusus penambah berat badan anak kanker.",
            "kwitansi_farmasi_01.pdf"
        ),
        (
            rayyan_id,
            "Biaya Akomodasi Ambulans & Rujukan Luar Kota",
            "Transportasi & Akomodasi",
            1200000.00,
            today - timedelta(days=3),
            "Sewa ambulans medis untuk rujukan rawat intensif dari puskesmas daerah ke rumah sakit rujukan provinsi.",
            "bukti_ambulans_01.pdf"
        ),
        (
            santri_id,
            "Pengadaan Beras Ramos 500 Kg & Lauk Protein",
            "Pangan Pokok",
            7500000.00,
            today - timedelta(days=7),
            "Pembelian 10 karung beras 50kg, 60 kg telur ayam broiler, tempe, dan daging ayam untuk menu santri selama dua pekan.",
            "nota_grosir_pangan.pdf"
        ),
        (
            jembatan_id,
            "Uang Muka Pembelian Sling Baja 24mm & Baut Baja",
            "Material Bangunan",
            5000000.00,
            today - timedelta(days=4),
            "Pembelian sling baja utama penahan beban jembatan beserta klem dan aksesoris tensioner dari distributor resmi.",
            "faktur_material_baja.pdf"
        )
    ]
    for c_id, title, cat, amt, exp_date, desc, doc in fund_usages:
        sql_fu = """
            INSERT INTO fund_usage_reports (
                campaign_id, expense_title, expense_category, amount,
                expense_date, description, proof_document
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(sql_fu, (c_id, title, cat, amt, exp_date, desc, doc), commit=True)
    print(f"[OK] Seeded {len(fund_usages)} fund usage transparency reports.")

    print("\n[SUCCESS] All demo data has been populated successfully!")
    print("-----------------------------------------------------------------")
    print("DEMO CREDENTIALS (All passwords: 'password123'):")
    print("1. Admin      : admin@donasikita.id")
    print("2. Fundraiser : lentera@donasikita.id, relawan@donasikita.id")
    print("3. Donatur    : budi@donasikita.id, siti@donasikita.id, ahmad@donasikita.id")
    print("-----------------------------------------------------------------")


def main():
    try:
        run_schema()
        seed_data()
    except Exception as e:
        print(f"\n[FATAL ERROR] Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
