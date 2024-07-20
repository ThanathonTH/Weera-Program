import os
import sys
import yt_dlp
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from PIL import Image, ImageTk
import requests
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
        url = self.check_clipboard()
        if not url:
            url = self.url_entry.get().strip()
        
        if url:
            if url not in self.url_listbox.get(0, tk.END):
                self.url_listbox.insert(tk.END, url)
                self.update_video_details()
            else:
                messagebox.showinfo("Info", "URL already in list.")
        else:
            messagebox.showwarning("Warning", "No valid URL found.")

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
                title = info_dict.get('title', 'No Title')
                duration = info_dict.get('duration', 0)
                thumbnail_url = info_dict.get('thumbnail', '')
                return title, duration, thumbnail_url
        except Exception as e:
            print(f"Error in get_video_details: {e}")
            return 'Error', 0, ''

    def update_thumbnail(self, image_url, thumbnail_label):
        try:
            response = requests.get(image_url)
            img_data = BytesIO(response.content)
            img = Image.open(img_data)
            img.thumbnail((120, 90))
            img = ImageTk.PhotoImage(img)
            self.root.after(0, lambda: self._update_thumbnail_label(thumbnail_label, img))
        except Exception as e:
            print(f"Failed to load thumbnail: {e}")
            self.root.after(0, lambda: self._update_thumbnail_label(thumbnail_label, None))

    def _update_thumbnail_label(self, thumbnail_label, img):
        if img:
            thumbnail_label.config(image=img)
            thumbnail_label.image = img
            self.thumbnail_images[thumbnail_label] = img  # Keep a reference to avoid garbage collection
        else:
            thumbnail_label.config(image='', text='No Thumbnail')

    def fetch_video_info(self, url):
        title, duration, thumbnail_url = self.get_video_details(url)
        return {
            'title': title,
            'duration': duration,
            'thumbnail_url': thumbnail_url
        }

    def update_video_details(self):
        for widget in self.details_inner_frame.winfo_children():
            widget.destroy()
        
        for url in self.url_listbox.get(0, tk.END):
            info = self.fetch_video_info(url)
            
            thumbnail_label = tk.Label(self.details_inner_frame)
            thumbnail_label.pack(side=tk.LEFT, padx=10, pady=10)
            self.update_thumbnail(info['thumbnail_url'], thumbnail_label)

            video_info = tk.Label(self.details_inner_frame, text=f"Title: {info['title']}\nDuration: {info['duration']} seconds")
            video_info.pack(side=tk.LEFT, padx=10, pady=10)
            
            self.video_info_labels[url] = video_info
            self.thumbnail_labels[url] = thumbnail_label

    def start_download(self):
        self.progress_var.set("Starting download...")
        self.progress_bar['value'] = 0
        self.downloaded_urls = 0
        self.total_urls = self.url_listbox.size()
        self.notification_shown = False  # Reset the notification flag
        
        if self.total_urls == 0:
            messagebox.showwarning("Warning", "No URLs to download.")
            return
        
        self.download_threads = []
        for url in self.url_listbox.get(0, tk.END):
            thread = threading.Thread(target=self.download_video, args=(url,))
            thread.start()
            self.download_threads.append(thread)
        
        # Start a thread to check download progress
        progress_thread = threading.Thread(target=self.check_download_progress)
        progress_thread.start()

    def download_video(self, url):
        output_path = self.output_path_var.get()
        if not output_path:
            output_path = '.'
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': False,
            'progress_hooks': [self.progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        self.downloaded_urls += 1
        if self.downloaded_urls == self.total_urls:
            self.root.after(0, self.show_completion_notification)

    def progress_hook(self, d):
        if d['status'] == 'finished':
            file_size = d.get('total_bytes', 0)
            downloaded = d.get('downloaded_bytes', 0)
            progress = (downloaded / file_size) * 100 if file_size > 0 else 100
            self.root.after(0, lambda: self.update_progress_bar(progress))
    
    def update_progress_bar(self, progress):
        self.progress_bar['value'] = progress
        self.progress_var.set(f"Progress: {progress:.2f}%")

    def check_download_progress(self):
        while any(thread.is_alive() for thread in self.download_threads):
            self.root.update_idletasks()
            self.root.after(100)
        
        self.root.after(0, self.show_completion_notification)

    def show_completion_notification(self):
        if not self.notification_shown:
            messagebox.showinfo("Completed", "ทำการโหลดครบหมดแล้ว")
            self.clear_all()
            self.notification_shown = True

    def clear_all(self):
        self.url_listbox.delete(0, tk.END)
        self.result_var.set("")
        self.progress_var.set("")
        self.progress_bar['value'] = 0
        self.clear_details()

    def clear_details(self):
        for widget in self.details_inner_frame.winfo_children():
            widget.destroy()

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_path_var.set(folder_selected)

    def remove_selected_url(self):
        selected_url_index = self.url_listbox.curselection()
        if selected_url_index:
            self.url_listbox.delete(selected_url_index[0])
            self.update_video_details()

    def clear_urls(self):
        self.url_listbox.delete(0, tk.END)
        self.clear_details()

def main():
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
