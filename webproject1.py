import threading
import requests
from bs4 import BeautifulSoup
from queue import Queue
import pickle
import os
import tkinter as tk
from tkinter import scrolledtext, messagebox
from tkinter import ttk
import time
import re

# --- Save crawler state ---
def save_state(visited, queue):
    with open("visited_urls.pkl", "wb") as f:
        pickle.dump(visited, f)
    with open("urls_to_visit.pkl", "wb") as f:
        pickle.dump(list(queue.queue), f)

# --- Load crawler state ---
def load_state():
    visited = set()
    queue = Queue()

    if os.path.exists("visited_urls.pkl"):
        with open("visited_urls.pkl", "rb") as f:
            visited = pickle.load(f)
    if os.path.exists("urls_to_visit.pkl"):
        with open("urls_to_visit.pkl", "rb") as f:
            for url in pickle.load(f):
                queue.put(url)

    return visited, queue

# --- Worker Thread Function ---
def crawl_worker(queue, visited, lock, result_text, progress_bar, num_threads):
    processed = 0
    while not queue.empty():
        url = queue.get()

        with lock:
            if url in visited:
                queue.task_done()
                continue
            visited.add(url)

        try:
            response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            
            if response.status_code != 200:
                queue.task_done()
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            with lock:
                result_text.insert(tk.END, f"Found: {url}\n")
                result_text.yview(tk.END)
                processed += 1
                progress_bar['value'] = (processed / num_threads) * 100
                progress_bar.update()

            for link in soup.find_all('a', href=True):
                abs_url = requests.compat.urljoin(url, link['href'])
                if abs_url.startswith('http') and abs_url not in visited:
                    with lock:
                        queue.put(abs_url)

        except requests.exceptions.RequestException as e:
            print(f"[-] Error crawling {url}: {e}")

        # Save state every 10 crawled pages
        with lock:
            if len(visited) % 10 == 0:
                save_state(visited, queue)

        queue.task_done()

    with lock:
        result_text.insert(tk.END, "[✓] Crawling complete.\n")
        result_text.yview(tk.END)

# --- Start Crawling ---
def start_crawling(start_url, num_threads, result_text, progress_bar):
    visited, url_queue = load_state()

    if url_queue.empty():
        if not re.match(r'^(http://|https://)', start_url):
            messagebox.showerror("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            return
        url_queue.put(start_url)

    lock = threading.Lock()
    threads = []

    for _ in range(num_threads):
        thread = threading.Thread(target=crawl_worker, args=(url_queue, visited, lock, result_text, progress_bar, num_threads))
        thread.daemon = True
        thread.start()
        threads.append(thread)

    url_queue.join()

# --- Tkinter UI Setup ---
def setup_ui():
    # Create main window
    root = tk.Tk()
    root.title("Web Crawler")
    root.geometry("700x600")
    root.config(bg="#2e2e2e")

    # Dark theme
    root.option_add("*background", "#2e2e2e")
    root.option_add("*foreground", "#ffffff")
    root.option_add("*font", "Helvetica 12")

    # Create a grid layout
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    # Label for instructions
    label = tk.Label(root, text="Enter URL to Start Crawling:", bg="#2e2e2e", fg="#ffffff")
    label.grid(row=0, column=0, pady=10, padx=10)

    # Entry for URL
    url_entry = tk.Entry(root, width=60)
    url_entry.grid(row=1, column=0, pady=10, padx=10)

    # ScrolledText for displaying results
    result_text = scrolledtext.ScrolledText(root, width=80, height=20, wrap=tk.WORD)
    result_text.grid(row=2, column=0, pady=10, padx=10)
    result_text.config(bg="#333333", fg="#ffffff", insertbackground="white")

    # Progress bar
    progress_bar = ttk.Progressbar(root, orient='horizontal', length=400, mode='determinate')
    progress_bar.grid(row=3, column=0, pady=10, padx=10)

    # Start Crawling Button
    def start_crawl():
        start_url = url_entry.get().strip()
        if start_url:
            result_text.delete(1.0, tk.END)
            progress_bar['value'] = 0  # Reset the progress bar
            threading.Thread(target=start_crawling, args=(start_url, 5, result_text, progress_bar), daemon=True).start()

    start_button = tk.Button(root, text="Start Crawling", command=start_crawl, bg="#4CAF50", fg="#ffffff")
    start_button.grid(row=4, column=0, pady=20)

    root.mainloop()

# --- Main Entry Point ---
if __name__ == "__main__":
    setup_ui()
