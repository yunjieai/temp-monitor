import os
import sys
import subprocess
import winsound
from PIL import Image

# 引入 Windows 視窗選擇工具
import tkinter as tk
from tkinter import filedialog

if os.name == 'nt':
    import msvcrt
    import ctypes  # 引入 Windows API 模組來控制視窗聚焦

def force_focus_console():
    """強制將當前的命令提示字元黑視窗帶到最前景並取得輸入焦點"""
    if os.name == 'nt':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

def get_job_config():
    """圖形化選單：讓使用者決定要選資料夾還是選單張/多張圖片"""
    force_focus_console()

    print("=== 圖片縮放工具 ===")
    print("請選擇您的選檔模式：")
    print("1. 選擇「 資料夾 」  (自動處理資料夾內所有圖片)")
    print("2. 挑選「 圖  片 」  (手動選取一張或多張圖片)")
    
    while True:
        choice = input("👉 請輸入模式 (1 或 2): ").strip()
        if choice in ('1', '2'):
            break
        print("輸入錯誤，請輸入 1 或 2。")

    target_files = []
    parent_dir = ""

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    if choice == '1':
        print("\n📬 請在彈出的視窗中，選擇您存放手機照片的資料夾...")
        selected_dir = filedialog.askdirectory(title="請選擇照片所在的資料夾")
        if selected_dir:
            parent_dir = os.path.normpath(selected_dir)
            valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
            try:
                for f in os.listdir(parent_dir):
                    if f.lower().endswith(valid_extensions):
                        target_files.append(f)
            except Exception as e:
                print(f"❌ 無法讀取資料夾: {e}")
    else:
        print("\n📬 請在彈出的視窗中，挑選您想處理的圖片 (可按住 Ctrl 鍵進行多選)...")
        file_paths = filedialog.askopenfilenames(
            title="請選取一張或多張圖片 (可按住 Ctrl 複選)",
            filetypes=[("圖片檔案", "*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if file_paths:
            file_list = list(file_paths)
            parent_dir = os.path.normpath(os.path.dirname(file_list[0]))
            target_files = [os.path.basename(f) for f in file_list]

    root.destroy()
    force_focus_console()
    
    if not parent_dir or not target_files:
        return None, []
        
    return parent_dir, target_files

def resize_images():
    current_dir, img_files = get_job_config()
    
    if not img_files:
        print("\n❌ 您取消了選擇，或者資料夾內找不到任何圖片。")
        print("\n💡 請按 [任意鍵] 或 [空白鍵] 結束程式...")
        if os.name == 'nt':
            msvcrt.getch()
        return

    output_dir = os.path.join(current_dir, "_SOP_processed")

    print(f"\n📂 目標主目錄: {current_dir}")
    print(f"📸 準備處理的圖片數量: {len(img_files)} 張\n")
    print("請選擇調整模式：")
    # 🌟 修改說明：將 200% 與 2 倍修改為 500% 與 5 倍
    print("1. 依「 % 」調整         (例如：輸入 50 縮小一半；輸入 300 放大三倍，上限為 500)")
    print("2. 指定「橫幅像素(寬度)」 (例如：輸入 720 或 1920，上限為原圖5倍)\n")
    
    while True:
        mode = input("👉 請輸入選項 (1 或 2): ").strip()
        if mode in ('1', '2'):
            break
        print("輸入錯誤，請輸入 1 或 2。")

    while True:
        try:
            val_input = input("👉 請輸入數值 (阿拉伯數字): ").strip()
            value = int(val_input)
            if value <= 0:
                print("數值必須大於 0！")
                continue
            break
        except ValueError:
            print("請輸入正確的阿拉伯數字！")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("\n🚀 開始處理圖片...")
    success_count = 0

    for filename in img_files:
        img_path = os.path.join(current_dir, filename)
        try:
            with Image.open(img_path) as img:
                try:
                    if hasattr(img, '_getexif'):
                        from PIL import ImageOps
                        img = ImageOps.exif_transpose(img)
                except Exception:
                    pass

                width, height = img.size
                is_limited = False
                
                if mode == '1':
                    # 🌟 核心修改點 A：將最大百分比安全鎖從 200 調整為 500
                    target_percent = value
                    if target_percent > 500:
                        target_percent = 500
                        is_limited = True
                        
                    scale = target_percent / 100.0
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                else:
                    # 🌟 核心修改點 B：將最大指定寬度安全鎖從 2 倍調整為原圖的 5 倍
                    max_allowed_width = width * 5
                    target_width = value
                    
                    if target_width > max_allowed_width:
                        target_width = max_allowed_width
                        is_limited = True
                        
                    new_width = target_width
                    new_height = int(height * (target_width / width))

                new_width = max(1, new_width)
                new_height = max(1, new_height)

                if new_width > width:
                    resample_method = Image.Resampling.BICUBIC
                    action_type = "放大"
                elif new_width < width:
                    resample_method = Image.Resampling.LANCZOS
                    action_type = "縮小"
                else:
                    resample_method = Image.Resampling.LANCZOS
                    action_type = "維持原樣"

                resized_img = img.resize((new_width, new_height), resample_method)
                
                # 🌟 修改提示：將 2 倍提示字改為 5 倍
                limit_msg = " ⚠️(已觸發最大 5 倍限制)" if is_limited else ""
                
                output_path = os.path.join(output_dir, filename)
                resized_img.save(output_path, quality=90)
                print(f" 🔹 已{action_type}: {filename} -> {new_width}x{new_height}{limit_msg}")
                success_count += 1
        except Exception as e:
            print(f" ❌ 處理失敗 {filename}: {e}")

    print(f"\n🎉 處理完畢！成功轉換 {success_count} 張圖片。")
    print(f"📁 圖片已存放在: {output_dir}")
    
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass
        
    print("\n💡 請按 [任意鍵] 或 [空白鍵] 結束程式並自動開啟新圖片資料夾...\n💡 by Robin")
    if os.name == 'nt':
        msvcrt.getch()
    else:
        subprocess.run(["open", output_dir])
        return
    
    try:
        os.startfile(output_dir)
    except Exception as e:
        print(f"無法自動開啟資料夾: {e}")

if __name__ == "__main__":
    resize_images()
