#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate preloaded reports JSON files for the React app.

This script scans ./preloaded_reports/ for folders containing .txt and .md files,
and generates JSON files in ./public/preloaded/ that the React app can fetch.

Usage:
    python generate_preloaded.py

Output:
    ./public/preloaded/index.json - List of available folders
    ./public/preloaded/<folder_name>.json - Contents of each folder
"""

import os
import json
import argparse

def process_file(file_path):
    """Read a file and return its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"  Warning: Could not read {file_path}: {e}")
        return None

def generate_preloaded_reports(input_dir='./preloaded_reports', output_dir='./public/preloaded'):
    """Generate JSON files from preloaded report folders."""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get list of folders in preloaded_reports
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return

    folders = []
    folder_entries = os.listdir(input_dir)

    for folder_name in sorted(folder_entries):
        folder_path = os.path.join(input_dir, folder_name)

        # Skip non-directories and hidden folders
        if not os.path.isdir(folder_path) or folder_name.startswith('.'):
            continue

        print(f"Processing folder: {folder_name}")

        # Get all .txt and .md files in the folder
        files_data = {}
        file_list = os.listdir(folder_path)
        text_files = [f for f in file_list if f.endswith('.txt') or f.endswith('.md')]
        text_files.sort(key=lambda x: x.lower())

        file_count = 0
        for filename in text_files:
            file_path = os.path.join(folder_path, filename)
            content = process_file(file_path)

            if content is not None:
                files_data[filename] = content
                file_count += 1
                print(f"  - {filename} ({len(content):,} chars)")

        if file_count > 0:
            # Save folder contents to JSON
            folder_json_path = os.path.join(output_dir, f"{folder_name}.json")
            with open(folder_json_path, 'w', encoding='utf-8') as f:
                json.dump(files_data, f, ensure_ascii=False, indent=2)
            print(f"  Saved to {folder_json_path}")

            folders.append({
                'name': folder_name,
                'fileCount': file_count
            })
        else:
            print(f"  No .txt or .md files found, skipping.")

    # Save index of all folders
    index_path = os.path.join(output_dir, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({'folders': folders}, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Generated index.json with {len(folders)} folder(s)")
    print(f"📁 Output directory: {output_dir}")

    return folders

def main():
    parser = argparse.ArgumentParser(description='Generate preloaded reports JSON files.')
    parser.add_argument('-i', '--input', default='./preloaded_reports',
                        help='Input directory containing report folders (default: ./preloaded_reports)')
    parser.add_argument('-o', '--output', default='./public/preloaded',
                        help='Output directory for JSON files (default: ./public/preloaded)')

    args = parser.parse_args()

    generate_preloaded_reports(args.input, args.output)

if __name__ == "__main__":
    main()
