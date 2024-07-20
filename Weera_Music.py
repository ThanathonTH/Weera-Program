import os
import sys
import requests
import yt_dlp
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from PIL import Image, ImageTk
from io import BytesIO
import threading
import pyperclip

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Weera_music")
        icon_path = os.path.join(sys._MEIPASS, 'photo', 'weera.ico') if getattr(sys, 'frozen', False) else 'photo/weera.ico'
        self.root.iconbitmap(icon_path)

        # Initialize variables
        self.video_info_labels = {}
        self.thumbnail_labels = {}
        self.thumbnail_images = {}  # To keep references to avoid garbage collection
        self.notification_shown = False  # Flag to ensure only one notification is shown
        self.download_threads = []  # To keep track of download threads
        self.total_urls = 0  # Total number of URLs to download
        self.downloaded_urls = 0  # Number of URLs that have been downloaded

        # Create and place widgets
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="YouTube Video URL:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.url_entry = tk.Entry(self.root, width=50)
        self.url_entry.grid(row=0, column=1, padx=10, pady=10)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="วาง", command=self.paste_url)
        self.url_entry.bind("<Button-3>", self.show_context_menu)

        tk.Button(self.root, text="Add URL", command=self.add_url).grid(row=0, column=2, padx=10, pady=10)

        # New button for checking updates
        tk.Button(self.root, text="ตรวจสอบอัพเดท", command=self.check_updates).grid(row=0, column=3, padx=10, pady=10)

        tk.Label(self.root, text="Download Location:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.output_path_var = tk.StringVar()
        self.output_path_entry = tk.Entry(self.root, textvariable=self.output_path_var, width=50)
        self.output_path_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Button(self.root, text="Browse", command=self.browse_folder).grid(row=1, column=2, padx=10, pady=10)

        tk.Button(self.root, text="Start Download", command=self.start_download).grid(row=2, column=0, columnspan=4, padx=10, pady=10)

        self.result_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.result_var).grid(row=3, column=0, columnspan=4, padx=10, pady=10)

        self.progress_var = tk.StringVar()
        self.progress_label = tk.Label(self.root, textvariable=self.progress_var)
        self.progress_label.grid(row=4, column=0, columnspan=4, padx=10, pady=10)

        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.grid(row=5, column=0, columnspan=4, padx=10, pady=10)

        self.url_frame = tk.Frame(self.root)
        self.url_frame.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        self.url_listbox = tk.Listbox(self.url_frame, width=80, height=10)
        self.url_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(self.url_frame, orient="vertical")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.url_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.url_listbox.yview)

        self.url_listbox.bind("<MouseWheel>", self.on_mouse_wheel)

        tk.Button(self.root, text="Clear List", command=self.clear_urls).grid(row=6, column=3, padx=10, pady=10)

        self.details_frame = tk.Frame(self.root)
        self.details_frame.grid(row=7, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

        self.details_canvas = tk.Canvas(self.details_frame)
        self.details_scrollbar = tk.Scrollbar(self.details_frame, orient="vertical", command=self.details_canvas.yview)
        self.details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.details_canvas.config(yscrollcommand=self.details_scrollbar.set)

        self.details_inner_frame = tk.Frame(self.details_canvas)
        self.details_canvas.create_window((0, 0), window=self.details_inner_frame, anchor="nw")
        self.details_inner_frame.bind("<Configure>", lambda e: self.details_canvas.configure(scrollregion=self.details_canvas.bbox("all")))

        self.details_canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.listbox_context_menu = tk.Menu(self.root, tearoff=0)
        self.listbox_context_menu.add_command(label="Remove", command=self.remove_selected_url)
        self.url_listbox.bind("<Button-3>", self.show_listbox_context_menu)

        # Status label for loading indication
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self.root, textvariable=self.status_var, fg="red")
        self.status_label.grid(row=8, column=0, columnspan=4, padx=10, pady=10)

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def show_listbox_context_menu(self, event):
        try:
            self.url_listbox.selection_clear(0, tk.END)
            self.url_listbox.selection_set(self.url_listbox.nearest(event.y))
            self.listbox_context_menu.post(event.x_root, event.y_root)
        finally:
            self.listbox_context_menu.grab_release()

    def on_mouse_wheel(self, event):
        if event.widget == self.details_canvas:
            self.details_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.widget == self.url_listbox:
            self.url_listbox.yview_scroll(int(-1*(event.delta/120)), "units")

    def paste_url(self):
        clipboard_content = pyperclip.paste().strip()
        if clipboard_content:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_content)

    def check_clipboard(self):
        clipboard_content = pyperclip.paste().strip()
        if clipboard_content and clipboard_content.startswith('https://www.youtube.com/'):
            return clipboard_content
        return None

    def add_url(self):
        self.status_var.set("กำลังโหลด...")
        self.status_label.update_idletasks()  # Update status label immediately
        thread = threading.Thread(target=self._add_url_thread)
        thread.start()

    def _add_url_thread(self):
        url = self.check_clipboard()
        if not url:
            url = self.url_entry.get().strip()
        
        if url:
            if url not in self.url_listbox.get(0, tk.END):
                self.root.after(0, lambda: self.url_listbox.insert(tk.END, url))
                self.root.after(0, self.update_video_details)
            else:
                self.root.after(0, lambda: messagebox.showinfo("Info", "URL already in list."))
        else:
            self.root.after(0, lambda: messagebox.showwarning("Warning", "No valid URL found."))
        
        # Clear status label text after processing
        self.root.after(0, lambda: self.status_var.set(""))

    def search_youtube(self, query):
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(f"ytsearch:{query}", download=False)
                if 'entries' in info_dict and len(info_dict['entries']) > 0:
                    return info_dict['entries'][0]['url'], info_dict['entries'][0]['title']
                return None, None
            except Exception as e:
                print(f"Error in search_youtube: {e}")
                return None, None

    def get_video_details(self, url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                title = info_dict.get('title', 'Unknown Title')
                duration = info_dict.get('duration', 0)
                thumbnail_url = info_dict.get('thumbnail', '')
                return title, duration, thumbnail_url
        except Exception as e:
            print(f"Error in get_video_details: {e}")
            return 'Unknown Title', 0, ''

    def update_video_details(self):
        urls = self.url_listbox.get(0, tk.END)
        for widget in self.details_inner_frame.winfo_children():
            widget.destroy()

        for url in urls:
            title, duration, thumbnail_url = self.get_video_details(url)
            title_label = tk.Label(self.details_inner_frame, text=f"Title: {title}")
            title_label.pack()
            duration_label = tk.Label(self.details_inner_frame, text=f"Duration: {duration} seconds")
            duration_label.pack()
            
            if thumbnail_url:
                try:
                    response = requests.get(thumbnail_url)
                    image = Image.open(BytesIO(response.content))
                    image = image.resize((120, 90), Image.ANTIALIAS)
                    thumbnail_image = ImageTk.PhotoImage(image)
                    
                    thumbnail_label = tk.Label(self.details_inner_frame, image=thumbnail_image)
                    thumbnail_label.image = thumbnail_image
                    thumbnail_label.pack()
                except Exception as e:
                    print(f"Error loading thumbnail: {e}")

    def start_download(self):
        self.status_var.set("กำลังดาวน์โหลด...")
        self.status_label.update_idletasks()
        
        urls = self.url_listbox.get(0, tk.END)
        download_location = self.output_path_var.get()

        if not download_location:
            messagebox.showwarning("Warning", "Please select a download location.")
            return

        self.total_urls = len(urls)
        self.downloaded_urls = 0
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = self.total_urls

        for url in urls:
            thread = threading.Thread(target=self._download_thread, args=(url, download_location))
            thread.start()
            self.download_threads.append(thread)

        # Wait for all threads to complete
        for thread in self.download_threads:
            thread.join()

        self.status_var.set("Download completed.")
        self.root.after(0, self.clear_urls)

    def _download_thread(self, url, download_location):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(download_location, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'progress_hooks': [self.progress_hook]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([url])
            except Exception as e:
                print(f"Error in download_thread: {e}")

    def progress_hook(self, d):
        if d['status'] == 'finished':
            self.downloaded_urls += 1
            self.root.after(0, lambda: self.progress_bar.config(value=self.downloaded_urls))
            self.root.after(0, lambda: self.progress_var.set(f"ดาวน์โหลด: {self.downloaded_urls}/{self.total_urls}"))

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_path_var.set(folder_selected)

    def clear_urls(self):
        self.url_listbox.delete(0, tk.END)
        self.details_inner_frame.destroy()
        self.details_inner_frame = tk.Frame(self.details_canvas)
        self.details_canvas.create_window((0, 0), window=self.details_inner_frame, anchor="nw")
        self.details_inner_frame.bind("<Configure>", lambda e: self.details_canvas.configure(scrollregion=self.details_canvas.bbox("all")))

    def remove_selected_url(self):
        selected = self.url_listbox.curselection()
        if selected:
            self.url_listbox.delete(selected[0])

    def check_updates(self):
        repo_url = "https://api.github.com/repos/ThanathonTH/Weera-Program/releases/latest"
        
        try:
            response = requests.get(repo_url)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release['tag_name']
            download_url = latest_release['assets'][0]['browser_download_url']
            
            current_version = "v1.0"  # Replace with your current version
            if latest_version != current_version:
                if messagebox.askyesno("Update Available", f"มีการอัพเดทใหม่ ({latest_version}) คุณต้องการดาวน์โหลดและติดตั้งตอนนี้ไหม?"):
                    self.download_update(download_url)
            else:
                messagebox.showinfo("Up to Date", "โปรแกรมของคุณเป็นเวอร์ชันล่าสุดแล้ว")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"ไม่สามารถตรวจสอบการอัพเดทได้: {e}")

    def download_update(self, download_url):
        try:
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open("update.zip", "wb") as file:
                    file.write(response.content)
                messagebox.showinfo("Update Downloaded", "การดาวน์โหลดอัพเดทเสร็จสิ้น กรุณารีสตาร์ทโปรแกรมเพื่อทำการติดตั้ง")
            else:
                messagebox.showerror("Error", "ไม่สามารถดาวน์โหลดการอัพเดทได้")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"ไม่สามารถดาวน์โหลดการอัพเดทได้: {e}")

def main():
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
