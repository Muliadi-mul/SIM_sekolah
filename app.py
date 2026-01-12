import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from flask import Blueprint

bp = Blueprint("guru", __name__, url_prefix="/guru")

# ---------- Config ----------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "sekolah.db")

UPLOAD_SISWA = os.path.join(APP_DIR, "static", "uploads_siswa")
UPLOAD_GURU = os.path.join(APP_DIR, "static", "uploads_guru")
os.makedirs(UPLOAD_SISWA, exist_ok=True)
os.makedirs(UPLOAD_GURU, exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

def hitung_selisih_tahun_bulan(tanggal_awal):
    """Mengembalikan selisih (tahun, bulan) dari tanggal_awal sampai hari ini"""
    if not tanggal_awal:
        return (0, 0)

    try:
        # Menangani format data yang mungkin datang dari database (YYYY-MM-DD)
        t_mulai = datetime.strptime(str(tanggal_awal), "%Y-%m-%d")
    except:
        return (0, 0)

    sekarang = datetime.today()
    r = relativedelta(sekarang, t_mulai)
    return (r.years, r.months)

def hitung_sisa_masa_kerja(tanggal_lahir):
    """
    Guru pensiun umur 60 tahun.
    Menghitung sisa masa kerja (tahun, bulan)
    """
    if not tanggal_lahir:
        return (0, 0)

    try:
        # Menangani format data yang mungkin datang dari database (YYYY-MM-DD)
        lahir = datetime.strptime(str(tanggal_lahir), "%Y-%m-%d")
    except:
        return (0, 0)

    # Menentukan tanggal pensiun (60 tahun setelah tanggal lahir)
    pensiun = lahir.replace(year=lahir.year + 60)
    sekarang = datetime.today()

    if pensiun < sekarang:
        return (0, 0)

    r = relativedelta(pensiun, sekarang)
    return (r.years, r.months)

def hitung_usia(tanggal_lahir):
    """
    FUNGSI BARU: Mengembalikan usia (tahun, bulan) dari tanggal_lahir sampai hari ini
    """
    if not tanggal_lahir:
        return (0, 0)

    try:
        lahir = datetime.strptime(str(tanggal_lahir), "%Y-%m-%d")
    except:
        return (0, 0)

    sekarang = datetime.today()
    r = relativedelta(sekarang, lahir)
    return (r.years, r.months)


app = Flask(__name__)
app.secret_key = "change_this_secret"
#app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.config['UPLOAD_FOLDER'] = 'static/uploads_siswa'
app.config['UPLOAD_FOLDER_GURU'] = 'static/uploads_guru'

# ---------- DB helpers ----------
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    conn = get_db()
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# ---------- Init DB ----------
def init_db():
    conn = get_db()
    c = conn.cursor()

    # Tabel Siswa
    c.execute("""CREATE TABLE IF NOT EXISTS siswa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama TEXT,
                    kelas TEXT,
                    jurusan TEXT,
                    tempat_lahir TEXT,
                    tanggal_lahir TEXT,
                    asal_sekolah TEXT,
                    usia_tahun INTEGER,
                    usia_bulan INTEGER,
                    alamat TEXT,
                    foto TEXT
                )""")

    # Tabel Guru (17 Kolom)
    c.execute("""CREATE TABLE IF NOT EXISTS guru (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama TEXT,
                    nip TEXT,
                    tempat_lahir TEXT,
                    tanggal_lahir TEXT,
                    agama TEXT,
                    jabatan TEXT,
                    nuptk TEXT,
                    sk_pertama TEXT,
                    sk_terakhir TEXT,
                    pendidikan TEXT,
                    mk_gol_tahun INTEGER,
                    mk_gol_bulan INTEGER,
                    mk_total_tahun INTEGER,
                    mk_total_bulan INTEGER,
                    sisa_mk_tahun INTEGER,
                    sisa_mk_bulan INTEGER,
                    foto TEXT
                )""")

    conn.commit()
    conn.close()

init_db()

# ---------- Utils ----------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def process_siswa_data(siswa_list):
    """Menghitung usia siswa secara real-time untuk ditampilkan"""
    processed = []
    for s in siswa_list:
        s_dict = dict(s)
        tgl_lahir = s_dict.get("tanggal_lahir")
        if tgl_lahir:
            usia_th, usia_bln = hitung_usia(tgl_lahir)
            # Menambahkan field realtime untuk display
            s_dict["usia_tahun_realtime"] = usia_th
            s_dict["usia_bulan_realtime"] = usia_bln
        else:
            s_dict["usia_tahun_realtime"] = 0
            s_dict["usia_bulan_realtime"] = 0
        processed.append(s_dict)
    return processed

# ---------- Routes: Dashboard ----------
@app.route("/dashboard")
@app.route("/")
def dashboard():
    total_siswa = query_db("SELECT COUNT(*) AS c FROM siswa", one=True)["c"]
    total_guru = query_db("SELECT COUNT(*) AS c FROM guru", one=True)["c"]
    total_kelas = query_db("SELECT COUNT(DISTINCT kelas) AS c FROM siswa", one=True)["c"]
    total_jurusan = query_db("SELECT COUNT(DISTINCT jurusan) AS c FROM siswa", one=True)["c"]

    # simple stats per jurusan for chart
    jurusan_rows = query_db("SELECT jurusan, COUNT(*) AS c FROM siswa GROUP BY jurusan")
    labels = [r["jurusan"] or "Undefined" for r in jurusan_rows]
    values = [r["c"] for r in jurusan_rows]

    return render_template("dashboard.html",
                            total_siswa=total_siswa,
                            total_guru=total_guru,
                            total_kelas=total_kelas,
                            total_jurusan=total_jurusan,
                            chart_labels=labels,
                            chart_values=values)

# ==========================
# CRUD SISWA
# ==========================
@app.route("/siswa")
def siswa_index():
    siswa = query_db("SELECT * FROM siswa ORDER BY nama ASC")
    # Hitung usia real-time sebelum dikirim ke template
    siswa_data = process_siswa_data(siswa)
    return render_template("siswa/index.html", siswa=siswa_data, keyword="")

@app.route("/siswa/tambah", methods=["GET", "POST"])
def siswa_tambah():
    if request.method == "POST":
        # Ambil data baru
        nama = request.form.get("nama")
        kelas = request.form.get("kelas")
        jurusan = request.form.get("jurusan")
        tempat_lahir = request.form.get("tempat_lahir")
        tanggal_lahir = request.form.get("tanggal_lahir")
        asal_sekolah = request.form.get("asal_sekolah")
        alamat = request.form.get("alamat")
        
        # Hitung usia otomatis
        usia_tahun, usia_bulan = hitung_usia(tanggal_lahir)

        foto_file = request.files.get("foto")
        foto_filename = None
        if foto_file and foto_file.filename != "" and allowed_file(foto_file.filename):
            foto_filename = secure_filename(foto_file.filename)
            foto_file.save(os.path.join(UPLOAD_SISWA, foto_filename))
        
        insert_values = (nama, kelas, jurusan, tempat_lahir, tanggal_lahir, asal_sekolah, 
                            usia_tahun, usia_bulan, alamat, foto_filename)

        # Menggunakan urutan kolom yang baru
        query_db("""INSERT INTO siswa (nama, kelas, jurusan, tempat_lahir, tanggal_lahir, 
                                        asal_sekolah, usia_tahun, usia_bulan, alamat, foto) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    insert_values)

        flash("Siswa berhasil ditambahkan.", "success")
        return redirect(url_for("siswa_index"))

    return render_template("siswa/tambah.html")

@app.route("/siswa/edit/<int:id>", methods=["GET", "POST"])
def siswa_edit(id):
    siswa = query_db("SELECT * FROM siswa WHERE id=?", (id,), one=True)
    if not siswa:
        flash("Data siswa tidak ditemukan.", "warning")
        return redirect(url_for("siswa_index"))

    # Hitung usia real-time untuk ditampilkan di form edit
    siswa_data = dict(siswa)
    usia_tahun, usia_bulan = hitung_usia(siswa_data.get("tanggal_lahir"))
    siswa_data["usia_tahun_realtime"] = usia_tahun
    siswa_data["usia_bulan_realtime"] = usia_bulan


    if request.method == "POST":
        # Ambil data baru
        nama = request.form.get("nama")
        kelas = request.form.get("kelas")
        jurusan = request.form.get("jurusan")
        tempat_lahir = request.form.get("tempat_lahir")
        tanggal_lahir = request.form.get("tanggal_lahir")
        asal_sekolah = request.form.get("asal_sekolah")
        alamat = request.form.get("alamat")
        
        # Hitung usia otomatis
        usia_tahun, usia_bulan = hitung_usia(tanggal_lahir)

        foto_file = request.files.get("foto")
        foto_filename = siswa["foto"]

        if foto_file and foto_file.filename != "" and allowed_file(foto_file.filename):
            # optionally delete old file (skip if you want to keep)
            if foto_filename:
                try:
                    os.remove(os.path.join(UPLOAD_SISWA, foto_filename))
                except Exception:
                    pass
            foto_filename = secure_filename(foto_file.filename)
            foto_file.save(os.path.join(UPLOAD_SISWA, foto_filename))
        
        update_values = (nama, kelas, jurusan, tempat_lahir, tanggal_lahir, asal_sekolah,
                            usia_tahun, usia_bulan, alamat, foto_filename, id)

        # Menggunakan urutan kolom yang baru
        query_db("""UPDATE siswa SET 
                    nama=?, kelas=?, jurusan=?, tempat_lahir=?, tanggal_lahir=?, 
                    asal_sekolah=?, usia_tahun=?, usia_bulan=?, alamat=?, foto=? 
                    WHERE id=?""",
                    update_values)

        flash("Data siswa berhasil diperbarui.", "success")
        return redirect(url_for("siswa_index"))

    return render_template("siswa/edit.html", siswa=siswa_data)

@app.route("/siswa/hapus/<int:id>")
def siswa_hapus(id):
    siswa = query_db("SELECT foto FROM siswa WHERE id=?", (id,), one=True)
    if siswa and siswa["foto"]:
        try:
            os.remove(os.path.join(UPLOAD_SISWA, siswa["foto"]))
        except Exception:
            pass
    query_db("DELETE FROM siswa WHERE id=?", (id,))
    flash("Data siswa dihapus.", "danger")
    return redirect(url_for("siswa_index"))

@app.route("/cari_siswa")
def cari_siswa():
    keyword = request.args.get("keyword", "")
    siswa = query_db("""SELECT * FROM siswa
                            WHERE nama LIKE ? OR kelas LIKE ? OR jurusan LIKE ? OR alamat LIKE ? OR asal_sekolah LIKE ? OR tempat_lahir LIKE ?
                            ORDER BY nama ASC""",
                            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    # Hitung usia real-time sebelum dikirim ke template
    siswa_data = process_siswa_data(siswa)
    return render_template("siswa/index.html", siswa=siswa_data, keyword=keyword)

# ==========================
# CRUD GURU
# ==========================

@bp.route("/")
def guru_index():
    guru = query_db("SELECT * FROM guru ORDER BY nama ASC")
    return render_template("guru/index.html", guru=guru)


@bp.route("/tambah", methods=["GET", "POST"])
def guru_tambah():
    if request.method == "POST":
        # 1. Ambil data mentah dari form (10 fields)
        nama = request.form.get("nama")
        nip = request.form.get("nip")
        tempat_lahir = request.form.get("tempat_lahir")
        tanggal_lahir = request.form.get("tanggal_lahir")
        agama = request.form.get("agama")
        jabatan = request.form.get("jabatan")
        nuptk = request.form.get("nuptk")
        sk_pertama = request.form.get("sk_pertama")
        sk_terakhir = request.form.get("sk_terakhir")
        pendidikan = request.form.get("pendidikan")
        
        # 2. Hitung Masa Kerja secara otomatis berdasarkan tanggal yang dimasukkan (6 fields)
        mk_total_tahun, mk_total_bulan = hitung_selisih_tahun_bulan(sk_pertama)
        mk_gol_tahun, mk_gol_bulan = hitung_selisih_tahun_bulan(sk_terakhir)
        sisa_mk_tahun, sisa_mk_bulan = hitung_sisa_masa_kerja(tanggal_lahir)

        foto_file = request.files.get("foto")
        foto_filename = None
        if foto_file and foto_file.filename != "" and allowed_file(foto_file.filename):
            foto_filename = secure_filename(foto_file.filename)
            foto_file.save(os.path.join(UPLOAD_GURU, foto_filename))

        # 3. Gabungkan data dalam urutan yang sesuai dengan kolom SQL (Total 17 values)
        insert_values = (
            nama, nip, tempat_lahir, tanggal_lahir, agama, jabatan, nuptk,
            sk_pertama, sk_terakhir, pendidikan, # Sumber data
            mk_gol_tahun, mk_gol_bulan, mk_total_tahun, mk_total_bulan, # Hasil perhitungan
            sisa_mk_tahun, sisa_mk_bulan,
            foto_filename # Foto
        )
        
        # 4. Simpan data yang sudah dihitung ke database.
        # PERBAIKAN UTAMA: Mengurangi jumlah placeholder (?) dari 18 menjadi 17.
        query_db("""INSERT INTO guru (
                    nama, nip, tempat_lahir, tanggal_lahir, agama, jabatan, nuptk,
                    sk_pertama, sk_terakhir, pendidikan, 
                    mk_gol_tahun, mk_gol_bulan, mk_total_tahun, mk_total_bulan,
                    sisa_mk_tahun, sisa_mk_bulan, foto)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    insert_values) # Tepat 17 values

        flash("Data guru berhasil ditambahkan.", "success")
        return redirect(url_for("guru.guru_index"))

    return render_template("guru/tambah.html")


@bp.route("/kartu/<int:id>")
def guru_kartu(id):
    guru = query_db("SELECT * FROM guru WHERE id=?", (id,), one=True)
    if not guru:
        flash("Data guru tidak ditemukan.", "warning")
        return redirect(url_for("guru.guru_index"))

    # Recalculate derived fields based on SK dates and Tgl Lahir for REAL-TIME display
    mk_total_tahun, mk_total_bulan = hitung_selisih_tahun_bulan(guru["sk_pertama"])
    mk_gol_tahun, mk_gol_bulan = hitung_selisih_tahun_bulan(guru["sk_terakhir"])
    sisa_tahun, sisa_bulan = hitung_sisa_masa_kerja(guru["tanggal_lahir"])

    # Update the dictionary for rendering
    guru = dict(guru)
    guru["mk_total_tahun"] = mk_total_tahun
    guru["mk_total_bulan"] = mk_total_bulan
    guru["mk_gol_tahun"] = mk_gol_tahun
    guru["mk_gol_bulan"] = mk_gol_bulan
    guru["sisa_mk_tahun"] = sisa_tahun
    guru["sisa_mk_bulan"] = sisa_bulan

    return render_template("guru/kartu.html", guru=guru)


@bp.route("/edit/<int:id>", methods=["GET", "POST"])
def guru_edit(id):
    guru = query_db("SELECT * FROM guru WHERE id=?", (id,), one=True)
    if not guru:
        flash("Data guru tidak ditemukan.", "warning")
        return redirect(url_for("guru.guru_index"))

    if request.method == "POST":
        # 1. Ambil data mentah dari form (10 fields)
        nama = request.form.get("nama")
        nip = request.form.get("nip")
        tempat_lahir = request.form.get("tempat_lahir")
        tanggal_lahir = request.form.get("tanggal_lahir")
        agama = request.form.get("agama")
        jabatan = request.form.get("jabatan")
        nuptk = request.form.get("nuptk")
        sk_pertama = request.form.get("sk_pertama")
        sk_terakhir = request.form.get("sk_terakhir")
        pendidikan = request.form.get("pendidikan")

        # 2. Hitung Masa Kerja secara otomatis berdasarkan tanggal yang dimasukkan (6 fields)
        mk_total_tahun, mk_total_bulan = hitung_selisih_tahun_bulan(sk_pertama)
        mk_gol_tahun, mk_gol_bulan = hitung_selisih_tahun_bulan(sk_terakhir)
        sisa_mk_tahun, sisa_mk_bulan = hitung_sisa_masa_kerja(tanggal_lahir)

        foto_file = request.files.get("foto")
        foto_filename = guru["foto"]

        if foto_file and foto_file.filename != "" and allowed_file(foto_file.filename):
            if foto_filename:
                try:
                    os.remove(os.path.join(UPLOAD_GURU, foto_filename))
                except:
                    pass
            foto_filename = secure_filename(foto_file.filename)
            foto_file.save(os.path.join(UPLOAD_GURU, foto_filename))

        # 3. Gabungkan data dalam urutan yang sesuai dengan kolom SQL baru (16 fields + foto + id)
        update_values = (
            nama, nip, tempat_lahir, tanggal_lahir, agama, jabatan, nuptk,
            sk_pertama, sk_terakhir, pendidikan, # Sumber data
            mk_gol_tahun, mk_gol_bulan, mk_total_tahun, mk_total_bulan, # Hasil perhitungan
            sisa_mk_tahun, sisa_mk_bulan,
            foto_filename, # Foto
            id # ID untuk WHERE (PENTING: ID harus di akhir)
        )

        # 4. Perbarui data di database dengan urutan kolom baru
        query_db("""
            UPDATE guru SET
                nama=?, nip=?, tempat_lahir=?, tanggal_lahir=?, agama=?, jabatan=?, nuptk=?,
                sk_pertama=?, sk_terakhir=?, pendidikan=?, 
                mk_gol_tahun=?, mk_gol_bulan=?, mk_total_tahun=?, mk_total_bulan=?,
                sisa_mk_tahun=?, sisa_mk_bulan=?,
                foto=? 
            WHERE id=?
        """, update_values)

        flash("Data guru berhasil diperbarui.", "success")
        return redirect(url_for("guru.guru_index"))

    return render_template("guru/edit.html", guru=guru)


@bp.route("/hapus/<int:id>")
def guru_hapus(id):
    guru = query_db("SELECT foto FROM guru WHERE id=?", (id,), one=True)
    if guru and guru["foto"]:
        try:
            os.remove(os.path.join(UPLOAD_GURU, guru["foto"]))
        except Exception:
            pass
    query_db("DELETE FROM guru WHERE id=?", (id,))
    flash("Data guru dihapus.", "danger")
    return redirect(url_for("guru.guru_index"))


@bp.route("/detail/<int:id>")
def guru_detail(id):
    guru = query_db("SELECT * FROM guru WHERE id = ?", [id], one=True)

    if not guru:
        flash("Data guru tidak ditemukan.", "warning")
        return redirect(url_for("guru.guru_index"))
    
    # Hitung Masa Kerja Total (berdasarkan SK_PERTAMA)
    masa_total_tahun, masa_total_bulan = hitung_selisih_tahun_bulan(guru["sk_pertama"])

    # Hitung Masa Kerja Golongan (berdasarkan SK_TERAKHIR)
    masa_golongan_tahun, masa_golongan_bulan = hitung_selisih_tahun_bulan(guru["sk_terakhir"])

    # Hitung Sisa Masa Kerja (berdasarkan Tanggal Lahir)
    sisa_tahun, sisa_bulan = hitung_sisa_masa_kerja(guru["tanggal_lahir"])

    # Format data untuk dikirim ke template
    masa_total = (masa_total_tahun, masa_total_bulan)
    masa_golongan = (masa_golongan_tahun, masa_golongan_bulan)
    sisa = (sisa_tahun, sisa_bulan)
    
    guru_data = dict(guru)
    
    return render_template(
        "guru/detail.html",
        guru=guru_data,
        masa_total=masa_total,
        masa_golongan=masa_golongan,
        sisa=sisa
    )

@bp.route("/import")
def guru_import():
    return render_template("guru/import.html", title="Import Guru")

app.register_blueprint(bp)

# ---------- run ----------
if __name__ == "__main__":
    app.run(debug=True)