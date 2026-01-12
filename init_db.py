import sqlite3
import os

# Define the database file path
# Nama database adalah 'sekolah.db'
DB_NAME = 'sekolah.db'

def setup_database():
    """Initializes the database and creates a table with 3 columns."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create the table with 3 columns (e.g., for school supplies inventory)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL
    );
    """)
    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} berhasil dibuat atau dibuka.")

def tambah_item_baru(item_id, name, quantity):
    """Fungsi praktis untuk menambahkan item baru ke tabel inventory."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        data = (item_id, name, quantity)
        # Gunakan INSERT OR IGNORE untuk mencegah error jika ID sudah ada
        query = "INSERT OR IGNORE INTO inventory (id, item_name, quantity) VALUES (?, ?, ?)"
        
        cursor.execute(query, data)
        conn.commit()
        
        # Cek apakah ada baris yang benar-benar dimasukkan
        if cursor.rowcount > 0:
            print(f"[SUCCESS] Berhasil menambahkan item: {name} (ID: {item_id})")
        else:
            print(f"[SKIP] Gagal menambahkan item: ID {item_id} sudah ada dalam database.")

    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan saat menambahkan item: {e}")
        
    finally:
        if conn:
            conn.close()

def lihat_semua_item():
    """Fungsi untuk mengambil dan menampilkan semua data dari tabel inventory."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, item_name, quantity FROM inventory ORDER BY id")
        items = cursor.fetchall()
        
        print("\n--- Data Inventory Sekolah Saat Ini ---")
        if items:
            print(f"{'ID':<5} | {'Nama Item':<30} | {'Jumlah':<10}")
            print("-" * 50)
            for item in items:
                print(f"{item[0]:<5} | {item[1]:<30} | {item[2]:<10}")
        else:
            print("Tabel inventory masih kosong.")
            
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan saat melihat data: {e}")
        
    finally:
        if conn:
            conn.close()

# --- Main execution ---
if __name__ == "__main__":
    # 1. Setup: Creates or opens sekolah.db
    setup_database()
    print("Pengaturan database selesai.")
    
    # 2. Add new data using the practical function
    print("\n--- Proses Penambahan Data ---")
    
    # Contoh data yang benar untuk dimasukkan
    tambah_item_baru(1, 'Buku Tulis A4', 500)
    tambah_item_baru(2, 'Pulpen Biru', 1500)
    tambah_item_baru(3, 'Spidol Papan Tulis', 50)
    tambah_item_baru(4, 'Peta Dunia', 5)
    tambah_item_baru(2, 'Pulpen Merah', 200) # Ini akan dilewati karena ID 2 sudah ada
    
    # 3. View the results
    lihat_semua_item()
    
    # 4. Cleanup step is REMOVED to keep sekolah.db persistent.
    print(f"\nSelesai. File database {DB_NAME} dipertahankan dan data ditampilkan.")