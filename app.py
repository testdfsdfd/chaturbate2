from flask import Flask, render_template_string, jsonify, request, session, send_file
import requests
import os
import json
from datetime import datetime
import time
import base64
import io

app = Flask(__name__)

# Helper functions
def country_to_flag(country_code):
    if not country_code or len(country_code) != 2:
        return ""
    offset = 127397
    return chr(ord(country_code[0].upper()) + offset) + chr(ord(country_code[1].upper()) + offset)

def gender_to_display(gender_code):
    gender_map = {
        'f': 'Female',
        'm': 'Male',
        't': 'Trans',
        'c': 'Couple'
    }
    return gender_map.get(gender_code.lower(), gender_code.capitalize())

def format_duration(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

# File paths
FAVORITES_FILE = 'data/favorites.json'
NOTES_FILE = 'data/notes.json'
PREFERENCES_FILE = 'data/preferences.json'
ROOM_CACHE_FILE = 'data/room_cache.json'
CLIPS_FILE = 'data/clips.json'

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Load/save data functions
def load_data(file_path, default=None):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except:
            return default if default is not None else {}
    return default if default is not None else {}

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f)

# HTML Template with all enhancements including clip capture
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharmLive - Enhanced Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #ff4d94;
            --secondary: #8a2be2;
            --dark: #0f0c1d;
            --darker: #090614;
            --card-bg: #1a1629;
            --text: #e6e1ff;
            --text-secondary: #a9a1d9;
            --success: #00e676;
            --error: #ff6b6b;
        }
        
        body.dark-mode {
            --dark: #121212;
            --darker: #000000;
            --card-bg: #1e1e1e;
            --text: #f5f5f5;
            --text-secondary: #aaaaaa;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, var(--darker), var(--dark));
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
            position: relative;
            overflow-x: hidden;
            transition: background 0.3s ease;
        }
        
        body::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at top right, rgba(138, 43, 226, 0.1), transparent 70%),
                        radial-gradient(circle at bottom left, rgba(255, 77, 148, 0.1), transparent 70%);
            z-index: -1;
        }
        
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(166, 153, 255, 0.1);
            flex-wrap: wrap;
            gap: 1.5rem;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(to right, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        
        .logo-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .controls {
            display: flex;
            gap: 1.5rem;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .filter-group {
            position: relative;
        }
        
        .filter-label {
            position: absolute;
            top: -10px;
            left: 15px;
            font-size: 0.8rem;
            background: var(--dark);
            padding: 0 5px;
            color: var(--text-secondary);
            z-index: 1;
        }
        
        select {
            background: rgba(20, 16, 41, 0.7);
            border: 1px solid rgba(166, 153, 255, 0.3);
            border-radius: 12px;
            padding: 0.85rem 1.5rem;
            color: var(--text);
            font-size: 1rem;
            backdrop-filter: blur(10px);
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 180px;
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23a9a1d9' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 1rem center;
            background-size: 1em;
        }
        
        select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(255, 77, 148, 0.2);
        }
        
        .stats {
            display: flex;
            gap: 1.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }
        
        .stat-card {
            background: rgba(20, 16, 41, 0.5);
            border: 1px solid rgba(166, 153, 255, 0.1);
            border-radius: 16px;
            padding: 1.2rem 1.8rem;
            backdrop-filter: blur(10px);
            min-width: 200px;
        }
        
        .stat-value {
            font-size: 2.2rem;
            font-weight: 600;
            background: linear-gradient(to right, var(--text), var(--text-secondary));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }
        
        .rooms-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.8rem;
            margin-top: 1.5rem;
        }
        
        .room-card {
            background: var(--card-bg);
            border-radius: 18px;
            overflow: hidden;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            position: relative;
            border: 1px solid rgba(166, 153, 255, 0.08);
        }
        
        .room-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 40px rgba(138, 43, 226, 0.25);
            border-color: rgba(138, 43, 226, 0.3);
        }
        
        .thumbnail {
            position: relative;
            height: 200px;
            overflow: hidden;
        }
        
        .thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }
        
        .room-card:hover .thumbnail img {
            transform: scale(1.05);
        }
        
        .live-badge {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 0, 85, 0.9);
            color: white;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.25rem 0.8rem;
            border-radius: 20px;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            animation: pulse 1.5s infinite;
            z-index: 2;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0.7); }
            70% { box-shadow: 0 0 0 8px rgba(255, 0, 85, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0); }
        }
        
        .viewer-count {
            position: absolute;
            bottom: 15px;
            left: 15px;
            background: rgba(0, 0, 0, 0.7);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.3rem;
            z-index: 2;
        }
        
        .card-content {
            padding: 1.5rem;
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .username {
            font-weight: 600;
            font-size: 1.3rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .gender-tag {
            font-size: 0.75rem;
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            background: rgba(138, 43, 226, 0.2);
        }
        
        .male {
            background: rgba(66, 135, 245, 0.2);
            color: #4287f5;
        }
        
        .female {
            background: rgba(255, 77, 148, 0.2);
            color: var(--primary);
        }
        
        .trans {
            background: rgba(101, 224, 101, 0.2);
            color: #65e065;
        }
        
        .couple {
            background: rgba(224, 101, 224, 0.2);
            color: #e065e0;
        }
        
        .tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 1rem 0;
        }
        
        .tag {
            background: rgba(166, 153, 255, 0.1);
            color: var(--text-secondary);
            font-size: 0.8rem;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            transition: all 0.2s ease;
        }
        
        .tag:hover {
            background: rgba(138, 43, 226, 0.3);
            color: var(--text);
        }
        
        .room-meta {
            display: flex;
            justify-content: space-between;
            margin-top: 1.2rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        
        .private-badge {
            background: rgba(255, 77, 148, 0.2);
            color: var(--primary);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .favorite-btn {
            position: absolute;
            top: 15px;
            left: 15px;
            background: rgba(0, 0, 0, 0.7);
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 2;
            transition: all 0.3s ease;
        }
        
        .favorite-btn:hover {
            background: rgba(255, 77, 148, 0.7);
            transform: scale(1.1);
        }
        
        .favorite-btn.favorited {
            background: rgba(255, 77, 148, 0.9);
        }
        
        .favorite-btn.favorited svg {
            fill: #fff;
        }
        
        #detail-box {
            background: var(--card-bg);
            border-radius: 18px;
            padding: 2rem;
            margin-top: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(166, 153, 255, 0.1);
            display: none;
        }
        
        .detail-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(166, 153, 255, 0.1);
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .nav-buttons {
            display: flex;
            gap: 0.5rem;
            margin: 0 1rem;
        }
        
        .nav-button {
            background: rgba(138, 43, 226, 0.3);
            color: white;
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .nav-button:hover {
            background: rgba(138, 43, 226, 0.7);
            transform: scale(1.1);
        }
        
        .nav-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .close-btn {
            background: rgba(255, 77, 148, 0.2);
            color: var(--primary);
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .close-btn:hover {
            background: rgba(255, 77, 148, 0.3);
            transform: rotate(90deg);
        }
        
        .detail-content {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }
        
        .video-container {
            grid-column: 1 / -1;
            position: relative;
            padding-bottom: 56.25%;
            height: 0;
            overflow: hidden;
            border-radius: 14px;
            background: #000;
        }
        
        .video-container iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(138, 43, 226, 0.3);
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 2rem auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .summary-card {
            display: flex;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }

        .summary-image {
            width: 200px;
            height: 200px;
            object-fit: cover;
            border-radius: 12px;
            border: 2px solid var(--primary);
        }

        .summary-details {
            flex: 1;
            min-width: 300px;
        }

        .summary-details h3 {
            margin-top: 0;
            color: var(--primary);
            font-size: 1.2rem;
        }

        .summary-details p {
            margin: 0.5rem 0;
        }

        .satisfaction-score {
            margin: 0.5rem 0;
        }

        .score-bar {
            width: 100%;
            height: 8px;
            background: rgba(166, 153, 255, 0.1);
            border-radius: 4px;
            margin: 0.3rem 0;
            overflow: hidden;
        }

        .score-fill {
            height: 100%;
            background: linear-gradient(to right, var(--primary), var(--secondary));
            border-radius: 4px;
        }

        .score-details {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .chat-rules {
            background: rgba(166, 153, 255, 0.1);
            padding: 0.8rem;
            border-radius: 8px;
            margin-top: 1rem;
            font-size: 0.9rem;
        }

        .error {
            color: var(--error);
        }
        
        .user-list-container {
            margin-top: 2rem;
            background: var(--card-bg);
            border-radius: 18px;
            padding: 1.5rem;
            border: 1px solid rgba(166, 153, 255, 0.1);
        }
        
        .user-list-title {
            font-size: 1.2rem;
            margin-bottom: 1rem;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .user-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 1rem;
        }
        
        .user-card {
            background: rgba(20, 16, 41, 0.5);
            border-radius: 12px;
            padding: 0.8rem;
            text-align: center;
            transition: all 0.2s ease;
        }
        
        .user-card:hover {
            background: rgba(138, 43, 226, 0.2);
            transform: translateY(-2px);
        }
        
        .user-icon {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: rgba(138, 43, 226, 0.2);
            margin: 0 auto 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: var(--primary);
        }
        
        .user-name {
            font-size: 0.9rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .user-gender {
            font-size: 0.7rem;
            color: var(--text-secondary);
            margin-top: 0.2rem;
        }
        
        .user-count {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 1rem;
        }
        
        .filter-section {
            background: var(--card-bg);
            border-radius: 18px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(166, 153, 255, 0.1);
        }
        
        .filter-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .search-box {
            position: relative;
            flex-grow: 1;
            max-width: 400px;
        }
        
        .search-box input {
            width: 100%;
            background: rgba(20, 16, 41, 0.7);
            border: 1px solid rgba(166, 153, 255, 0.3);
            border-radius: 12px;
            padding: 0.85rem 1.5rem 0.85rem 3rem;
            color: var(--text);
            font-size: 1rem;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }
        
        .search-box input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(255, 77, 148, 0.2);
        }
        
        .search-icon {
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
        }
        
        .tags-board-container {
            max-height: 200px;
            overflow-y: auto;
            padding-right: 0.5rem;
            margin-top: 1rem;
        }
        
        .tags-board {
            display: flex;
            flex-wrap: wrap;
            gap: 0.8rem;
        }
        
        .filter-tag {
            background: rgba(166, 153, 255, 0.1);
            color: var(--text-secondary);
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            transition: all 0.2s ease;
            cursor: pointer;
            border: 1px solid transparent;
        }
        
        .filter-tag:hover {
            background: rgba(138, 43, 226, 0.3);
            color: var(--text);
        }
        
        .filter-tag.active {
            background: rgba(255, 77, 148, 0.2);
            color: var(--primary);
            border-color: var(--primary);
        }
        
        .filter-title {
            font-size: 1.2rem;
            margin-bottom: 1rem;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .range-container {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-content {
            background: var(--card-bg);
            padding: 2rem;
            border-radius: 12px;
            width: 80%;
            max-width: 500px;
        }
        
        .modal-content textarea {
            width: 100%;
            min-height: 100px;
            margin: 1rem 0;
            background: var(--dark);
            color: var(--text);
            border: 1px solid var(--secondary);
            padding: 0.5rem;
            border-radius: 8px;
        }
        
        .toggle-dark-mode {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--primary);
            color: white;
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }
        
        .new-badge {
            background: var(--success);
            color: white;
            font-size: 0.7rem;
            padding: 0.2rem 0.5rem;
            border-radius: 12px;
            margin-left: 0.5rem;
        }
        
        .social-links {
            margin-top: 1rem;
        }
        
        .social-links a {
            display: inline-block;
            margin-right: 0.5rem;
            color: var(--primary);
            text-decoration: none;
        }
        
        .import-export {
            margin-top: 1rem;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }
        
        .import-export button {
            background: rgba(138, 43, 226, 0.3);
            color: var(--text);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .import-export button:hover {
            background: rgba(138, 43, 226, 0.5);
        }
        
        .user-note {
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(166, 153, 255, 0.1);
            border-radius: 8px;
        }
        
        .user-note h4 {
            margin-bottom: 0.5rem;
            color: var(--primary);
        }
        
        .user-note p {
            margin: 0;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--card-bg);
            color: var(--text);
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 10px;
            transform: translateX(200%);
            transition: transform 0.3s ease;
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification-close {
            background: transparent;
            border: none;
            color: var(--text);
            cursor: pointer;
            font-size: 1.2rem;
        }
        
        .tags-board-container::-webkit-scrollbar {
            width: 8px;
        }
        
        .tags-board-container::-webkit-scrollbar-track {
            background: rgba(20, 16, 41, 0.5);
            border-radius: 10px;
        }
        
        .tags-board-container::-webkit-scrollbar-thumb {
            background: rgba(166, 153, 255, 0.3);
            border-radius: 10px;
        }
        
        .tags-board-container::-webkit-scrollbar-thumb:hover {
            background: rgba(166, 153, 255, 0.5);
        }
        
        /* Clip capture styles */
        .clip-controls {
            margin: 1rem 0;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        #record-button {
            background: rgba(255, 77, 148, 0.3);
            color: var(--text);
            border: none;
            padding: 0.7rem 1.2rem;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        #record-button:hover:not(:disabled) {
            background: rgba(255, 77, 148, 0.5);
        }
        
        #record-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        #recording-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .recording-indicator {
            width: 12px;
            height: 12px;
            background-color: var(--error);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        
        .clips-container {
            margin-top: 2rem;
            background: var(--card-bg);
            border-radius: 18px;
            padding: 1.5rem;
            border: 1px solid rgba(166, 153, 255, 0.1);
        }
        
        .clips-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .clip-item {
            background: rgba(20, 16, 41, 0.5);
            border-radius: 12px;
            padding: 0.8rem;
            transition: all 0.2s ease;
            position: relative;
        }
        
        .clip-item:hover {
            background: rgba(138, 43, 226, 0.2);
        }
        
        .clip-item video {
            width: 100%;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        
        .clip-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .delete-clip {
            background: rgba(255, 77, 148, 0.2);
            color: var(--primary);
            border: none;
            padding: 0.3rem 0.6rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .delete-clip:hover {
            background: rgba(255, 77, 148, 0.3);
        }
        
        .no-clips {
            text-align: center;
            color: var(--text-secondary);
            padding: 2rem;
        }
        
        @media (max-width: 768px) {
            .rooms-grid {
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            }
            
            .detail-content {
                grid-template-columns: 1fr;
            }
            
            header {
                flex-direction: column;
                gap: 1.5rem;
                align-items: flex-start;
            }
            
            .controls {
                width: 100%;
            }
            
            .summary-card {
                flex-direction: column;
            }
            
            .summary-image {
                width: 100%;
                height: auto;
                max-height: 300px;
            }
            
            .user-grid {
                grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            }
            
            .filter-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }
            
            .search-box {
                max-width: 100%;
                width: 100%;
            }
            
            .tags-board-container {
                max-height: 150px;
            }
            
            .nav-buttons {
                margin: 0 0.5rem;
            }
            
            .modal-content {
                width: 90%;
                padding: 1rem;
            }
            
            .import-export {
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .clips-grid {
                grid-template-columns: 1fr;
            }
        }
        
        @media (max-width: 480px) {
            .stat-card {
                min-width: 100%;
            }
            
            .room-card {
                width: 100%;
            }
            
            .clip-controls {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>
</head>
<body class="{{ 'dark-mode' if preferences.dark_mode else '' }}">
    <header>
        <div class="logo">
            <div class="logo-icon">✦</div>
            <span>CharmLive</span>
        </div>
        <div class="controls">
            <div class="filter-group">
                <span class="filter-label">Quick Filter</span>
                <select id="quick-filter" onchange="filterRooms()">
                    <option value="">All Streams</option>
                    <option value="f">Female</option>
                    <option value="m">Male</option>
                    <option value="t">Trans</option>
                    <option value="c">Couple</option>
                </select>
            </div>
            <div class="filter-group">
                <span class="filter-label">Favorites</span>
                <select id="favorites-filter" onchange="filterFavorites()">
                    <option value="all">All Streams</option>
                    <option value="favorites">Only Favorites</option>
                </select>
            </div>
            <div class="filter-group">
                <span class="filter-label">Sort By</span>
                <select id="sort-by" onchange="sortRooms(this.value)">
                    <option value="viewers-desc">Most Viewers</option>
                    <option value="viewers-asc">Fewest Viewers</option>
                    <option value="alphabetical">A-Z</option>
                    <option value="newest">Newest</option>
                </select>
            </div>
        </div>
    </header>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{{ "{:,}".format(rooms|length) }}</div>
            <div class="stat-label">Active Streams</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ "{:,}".format(total_viewers) }}</div>
            <div class="stat-label">Total Viewers</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ "{:,}".format(private_rooms) }}</div>
            <div class="stat-label">Private Shows</div>
        </div>
    </div>

    <div class="filter-section">
        <div class="filter-header">
            <h3 class="filter-title">Advanced Filters</h3>
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="broadcaster-search" placeholder="Search broadcasters..." oninput="searchBroadcasters()">
            </div>
        </div>
        <div class="filter-group">
            <span class="filter-label">Viewers Range</span>
            <div class="range-container">
                <input type="range" id="viewer-min" min="0" max="1000" value="{{ preferences.viewer_min or 0 }}" oninput="updateViewerFilter()">
                <span id="viewer-min-value">{{ preferences.viewer_min or 0 }}</span>
                <input type="range" id="viewer-max" min="0" max="10000" value="{{ preferences.viewer_max or 10000 }}" oninput="updateViewerFilter()">
                <span id="viewer-max-value">{{ preferences.viewer_max or 10000 }}</span>
            </div>
        </div>
        <div class="filter-group">
            <span class="filter-label">Show Type</span>
            <select id="show-type" onchange="filterRooms()">
                <option value="all">All Shows</option>
                <option value="public">Public Only</option>
                <option value="private">Private Only</option>
            </select>
        </div>
        <div class="filter-group">
            <h3 class="filter-title">Filter by Tags</h3>
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="tag-search" placeholder="Search tags..." oninput="searchTags()">
            </div>
            <div class="tags-board-container">
                <div class="tags-board" id="tags-board">
                    {% for t in all_tags %}
                        <div class="filter-tag" onclick="toggleTagFilter('{{ t }}')">{{ t }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    
    <div class="rooms-grid" id="rooms">
        {% for room in rooms %}
        <div class="room-card" 
             data-tags="{{ room.tags | join(',') | lower }}" 
             data-gender="{{ room.gender }}"
             data-username="{{ room.username }}"
             data-viewers="{{ room.num_users }}"
             data-start-time="{{ room.start_time }}"
             onclick="loadDetails('{{ room.username }}')">
            <div class="thumbnail">
                <button class="favorite-btn" onclick="toggleFavorite(event, '{{ room.username }}')">
                    <svg width="16" height="16" viewBox="0 0 24 24">
                        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
                    </svg>
                </button>
                <img loading="lazy" 
                     src="https://jpeg.live.mmcdn.com/stream?room={{ room.username }}&f=1&t={{ timestamp }}" 
                     alt="{{ room.username }}" 
                     class="lazy room-thumbnail"
                     data-username="{{ room.username }}">
                <div class="live-badge">
                    <span>●</span> LIVE
                </div>
                <div class="viewer-count">
                    👁️ {{ "{:,}".format(room.num_users) }} viewers
                </div>
                {% if room.is_new %}
                <div class="new-badge">NEW</div>
                {% endif %}
            </div>
            <div class="card-content">
                <div class="card-header">
                    <div class="username">
                        {{ room.username }}
                        <span class="gender-tag {{ room.gender_display.lower() }}">{{ room.gender_display }}</span>
                    </div>
                    <div class="private-badge">
                        {{ 'Private: $' + "{:,}".format(room.private_price) if room.private_price > 0 else 'Public' }}
                    </div>
                </div>
                
                <div class="location">
                    {% if room.flag %}{{ room.flag }} {% endif %}{{ room.location or 'Unknown' }}
                </div>
                
                <div class="tags">
                    {% if room.tags %}
                        {% for tag in room.tags[:3] %}
                            <span class="tag">{{ tag }}</span>
                        {% endfor %}
                    {% else %}
                        <span class="tag">No tags</span>
                    {% endif %}
                </div>
                
                <div class="room-meta">
                    <div>⏱️ {{ format_duration(room.uptime) }}</div>
                    <div>❤️ {{ "{:,}".format(room.num_followers) }} followers</div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <div id="detail-box">
        <div class="detail-header">
            <h2 id="detail-username"></h2>
            <div class="nav-buttons" id="nav-buttons" style="display: none;">
                <button class="nav-button prev" onclick="navigateFavorite(-1)">←</button>
                <button class="nav-button next" onclick="navigateFavorite(1)">→</button>
            </div>
            <button class="close-btn" onclick="closeDetails()">×</button>
        </div>
        
        <div class="detail-content">
            <div class="video-container">
                <iframe id="video-frame" src="" frameborder="0" allowfullscreen></iframe>
            </div>
            
            <div class="detail-panel">
                <h3 class="panel-title">Room Summary</h3>
                <div id="panel-info" class="summary-card"></div>
                
                <!-- Clip capture controls -->
                <div class="clip-controls">
                    <button id="record-button" onclick="startRecording()">⏺ Record 30s Clip</button>
                    <div id="recording-status" style="display: none;">
                        <div class="recording-indicator"></div>
                        <span id="countdown">30s</span>
                    </div>
                </div>
                
                <div class="import-export">
                    <button onclick="exportFavorites()">Export Favorites</button>
                    <input type="file" id="import-file" accept=".json" style="display: none;" onchange="importFavorites(event)">
                    <button onclick="document.getElementById('import-file').click()">Import Favorites</button>
                    <button onclick="showNotesModal(currentUsername)">Add Note</button>
                </div>
            </div>
            
            <!-- Clips display section -->
            <div id="clips-container" class="clips-container">
                <h3 class="user-list-title">🎬 Recorded Clips</h3>
                <div id="clips-list" class="clips-grid"></div>
            </div>
            
            <div id="user-list-container" class="user-list-container">
                <h3 class="user-list-title">👥 Current Viewers</h3>
                <div id="user-count" class="user-count">Loading users...</div>
                <div id="user-grid" class="user-grid"></div>
            </div>
        </div>
    </div>

    <button class="toggle-dark-mode" onclick="toggleDarkMode()">🌓</button>

    <script>
    // Global variables
    let favorites = new Set();
    let currentFavIndex = 0;
    let favRooms = [];
    let currentUsername = '';
    let currentSortMethod = 'viewers-desc';
    let updateInterval;
    let activeTags = new Set();
    let notes = {};
    let lastOnlineStatus = {};
    let hoverRefreshIntervals = {};
    let globalRefreshInterval;
    
    // Clip recording variables
    let mediaRecorder = null;
    let recordedChunks = [];
    let recordingInterval = null;
    let recordingTimeLeft = 30;
    let stream = null;
    
    // Initialize the dashboard
    document.addEventListener('DOMContentLoaded', function() {
        loadFavorites();
        loadPreferences();
        loadNotes();
        requestNotificationPermission();
        startUpdates();
        initializeIntersectionObserver();
        setupThumbnailRefresh();
        
        // Set up event listeners
        document.addEventListener('keydown', handleKeyDown);
        
        // Apply initial filters and sorting
        filterRooms();
        sortRooms(currentSortMethod);
        
        // Set initial values from preferences
        document.getElementById('quick-filter').value = "{{ preferences.quick_filter or '' }}";
        document.getElementById('favorites-filter').value = "{{ preferences.favorites_filter or 'all' }}";
        document.getElementById('sort-by').value = "{{ preferences.sort_method or 'viewers-desc' }}";
        document.getElementById('show-type').value = "{{ preferences.show_type or 'all' }}";
    });
    
    // Thumbnail refresh setup
    function setupThumbnailRefresh() {
        // Add hover event listeners to room cards
        document.querySelectorAll('.room-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                startHoverRefresh(card);
            });
            
            card.addEventListener('mouseleave', () => {
                stopHoverRefresh(card.dataset.username);
            });
        });
        
        // Start global thumbnail refresh
        startGlobalThumbnailRefresh();
    }
    
    function refreshThumbnail(imgElement) {
        const username = imgElement.dataset.username;
        const timestamp = new Date().getTime();
        imgElement.src = `https://jpeg.live.mmcdn.com/stream?room=${username}&f=1&t=${timestamp}`;
    }
    
    function startHoverRefresh(roomCard) {
        const img = roomCard.querySelector('.room-thumbnail');
        if (!img) return;
        
        // Refresh immediately
        refreshThumbnail(img);
        
        // Start refreshing every 100ms
        hoverRefreshIntervals[roomCard.dataset.username] = setInterval(() => {
            refreshThumbnail(img);
        }, 100);
    }
    
    function stopHoverRefresh(username) {
        if (hoverRefreshIntervals[username]) {
            clearInterval(hoverRefreshIntervals[username]);
            delete hoverRefreshIntervals[username];
        }
    }
    
    function startGlobalThumbnailRefresh() {
        // Refresh all thumbnails every 10 seconds
        globalRefreshInterval = setInterval(() => {
            document.querySelectorAll('.room-thumbnail:not([data-refreshing])').forEach(img => {
                refreshThumbnail(img);
            });
        }, 10000);
    }
    
    // Load data functions
    function loadFavorites() {
        fetch('/get_favorites')
            .then(response => response.json())
            .then(data => {
                favorites = new Set(data.favorites);
                updateFavoriteButtons();
                filterFavorites();
            });
    }
    
    function loadPreferences() {
        fetch('/get_preferences')
            .then(response => response.json())
            .then(data => {
                if (data.dark_mode) {
                    document.body.classList.add('dark-mode');
                }
                document.getElementById('viewer-min').value = data.viewer_min || 0;
                document.getElementById('viewer-max').value = data.viewer_max || 10000;
                document.getElementById('viewer-min-value').textContent = data.viewer_min || 0;
                document.getElementById('viewer-max-value').textContent = data.viewer_max || 10000;
                currentSortMethod = data.sort_method || 'viewers-desc';
                
                // Initialize active tags from preferences
                if (data.active_tags) {
                    activeTags = new Set(data.active_tags);
                    activeTags.forEach(tag => {
                        const tagElements = document.querySelectorAll('.filter-tag');
                        tagElements.forEach(el => {
                            if (el.textContent === tag) {
                                el.classList.add('active');
                            }
                        });
                    });
                }
            });
    }
    
    function loadNotes() {
        fetch('/get_notes')
            .then(response => response.json())
            .then(data => {
                notes = data;
            });
    }
    
    // Save data functions
    function saveFavorites() {
        fetch('/save_favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({favorites: Array.from(favorites)})
        });
    }
    
    function savePreferences() {
        const preferences = {
            dark_mode: document.body.classList.contains('dark-mode'),
            quick_filter: document.getElementById('quick-filter').value,
            favorites_filter: document.getElementById('favorites-filter').value,
            sort_method: document.getElementById('sort-by').value,
            viewer_min: document.getElementById('viewer-min').value,
            viewer_max: document.getElementById('viewer-max').value,
            show_type: document.getElementById('show-type').value,
            active_tags: Array.from(activeTags)
        };
        
        fetch('/save_preferences', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(preferences)
        });
    }
    
    function saveNotes() {
        fetch('/save_notes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(notes)
        });
    }
    
    // UI interaction functions
    function toggleFavorite(event, username) {
        event.stopPropagation();
        
        if (favorites.has(username)) {
            favorites.delete(username);
        } else {
            favorites.add(username);
        }
        
        saveFavorites();
        updateFavoriteButtons();
        filterFavorites();
    }
    
    function updateFavoriteButtons() {
        document.querySelectorAll('.room-card').forEach(card => {
            const username = card.dataset.username;
            const btn = card.querySelector('.favorite-btn');
            
            if (favorites.has(username)) {
                btn.classList.add('favorited');
            } else {
                btn.classList.remove('favorited');
            }
        });
    }
    
    function filterFavorites() {
        const filter = document.getElementById("favorites-filter").value;
        const rooms = document.querySelectorAll('.room-card');
        
        favRooms = [];
        
        rooms.forEach(room => {
            const username = room.dataset.username;
            if (filter === 'favorites') {
                if (favorites.has(username)) {
                    room.style.display = 'block';
                    favRooms.push(username);
                } else {
                    room.style.display = 'none';
                }
            } else {
                room.style.display = 'block';
            }
        });
        
        const navButtons = document.getElementById('nav-buttons');
        navButtons.style.display = filter === 'favorites' ? 'flex' : 'none';
        savePreferences();
    }
    
    function sortRooms(criteria) {
        const grid = document.getElementById('rooms');
        const rooms = Array.from(grid.children);
        
        rooms.sort((a, b) => {
            const aViewers = parseInt(a.dataset.viewers);
            const bViewers = parseInt(b.dataset.viewers);
            const aStart = parseInt(a.dataset.startTime);
            const bStart = parseInt(b.dataset.startTime);
            
            switch(criteria) {
                case 'viewers-desc':
                    return bViewers - aViewers;
                case 'viewers-asc':
                    return aViewers - bViewers;
                case 'alphabetical':
                    return a.dataset.username.localeCompare(b.dataset.username);
                case 'newest':
                    return bStart - aStart;
                default:
                    return 0;
            }
        });
        
        rooms.forEach(room => grid.appendChild(room));
        currentSortMethod = criteria;
        savePreferences();
    }
    
    function updateViewerFilter() {
        const min = document.getElementById('viewer-min').value;
        const max = document.getElementById('viewer-max').value;
        document.getElementById('viewer-min-value').textContent = min;
        document.getElementById('viewer-max-value').textContent = max;
        filterRooms();
        savePreferences();
    }
    
    function filterRooms() {
        const genderFilter = document.getElementById('quick-filter').value;
        const viewerMin = parseInt(document.getElementById('viewer-min').value);
        const viewerMax = parseInt(document.getElementById('viewer-max').value);
        const showType = document.getElementById('show-type').value;
        const rooms = document.querySelectorAll('.room-card');
        
        rooms.forEach(room => {
            const roomGender = room.dataset.gender;
            const roomViewers = parseInt(room.dataset.viewers);
            const isPrivate = room.querySelector('.private-badge').textContent.includes('Private');
            const roomTags = room.dataset.tags;
            
            // Check gender filter
            const genderMatch = !genderFilter || roomGender === genderFilter;
            
            // Check viewer count
            const viewerMatch = roomViewers >= viewerMin && roomViewers <= viewerMax;
            
            // Check show type
            const typeMatch = showType === 'all' || 
                             (showType === 'public' && !isPrivate) || 
                             (showType === 'private' && isPrivate);
            
            // Check tags
            let tagMatch = true;
            if (activeTags.size > 0) {
                tagMatch = Array.from(activeTags).some(tag => 
                    roomTags.includes(tag.toLowerCase())
                );
            }
            
            if (genderMatch && viewerMatch && typeMatch && tagMatch) {
                room.style.display = 'block';
            } else {
                room.style.display = 'none';
            }
        });
        
        sortRooms(currentSortMethod);
    }
    
    // Detail view functions
    function loadDetails(username) {
        currentUsername = username;
        const box = document.getElementById("detail-box");
        const usernameEl = document.getElementById("detail-username");
        const videoFrame = document.getElementById("video-frame");
        const panelInfo = document.getElementById("panel-info");
        const userGrid = document.getElementById("user-grid");
        const userCount = document.getElementById("user-count");
        
        box.style.display = "block";
        usernameEl.textContent = `${username} ⋆`;
        panelInfo.innerHTML = '<div class="spinner"></div>';
        userGrid.innerHTML = '';
        userCount.textContent = 'Loading users...';
        
        videoFrame.src = `https://chaturbate.com/embed/${username}/?bgcolor=black&embed_video_only=1&disable_sound=0`;
        
        if (document.getElementById("favorites-filter").value === 'favorites') {
            currentFavIndex = favRooms.indexOf(username);
            updateNavigationButtons();
        }
        
        fetch(`/room/${username}/summary`)
            .then(response => response.json())
            .then(summary => {
                if (summary.error) throw new Error(summary.error);
                
                let noteContent = notes[username] || '';
                
                panelInfo.innerHTML = `
                    <div>
                        <img src="${summary.summary_card_image}" 
                             alt="${username}" 
                             class="summary-image"
                             onerror="this.src='https://i.imgur.com/3Zx5XeI.png'">
                    </div>
                    <div class="summary-details">
                        <h3>${summary.room_title}</h3>
                        <p><strong>Viewers:</strong> ${formatNumber(summary.num_viewers)}</p>
                        <p><strong>Gender:</strong> ${summary.broadcaster_gender}</p>
                        ${summary.private_show_price > 0 ? 
                          `<p><strong>Private Show:</strong> $${formatNumber(summary.private_show_price)}/min</p>` : ''}
                        <p><strong>Stream Quality:</strong> ${summary.quality}</p>
                        <div class="satisfaction-score">
                            <strong>Satisfaction:</strong>
                            <div class="score-bar">
                                <div class="score-fill" style="width: ${summary.satisfaction_score.percent}%"></div>
                            </div>
                            <div class="score-details">
                                ${summary.satisfaction_score.percent}% (${formatNumber(summary.satisfaction_score.up_votes)} 👍 / 
                                ${formatNumber(summary.satisfaction_score.down_votes)} 👎)
                            </div>
                        </div>
                        ${summary.chat_rules ? 
                          `<div class="chat-rules"><strong>Chat Rules:</strong> ${summary.chat_rules}</div>` : ''}
                        ${summary.social_links ? 
                          `<div class="social-links">
                              <h4>Social Media</h4>
                              ${summary.social_links.map(link => `
                                  <a href="${link.url}" target="_blank">${link.platform}</a>
                              `).join('')}
                          </div>` : ''}
                        <div class="user-note">
                            <h4>Your Note</h4>
                            <p>${noteContent || 'No note yet'}</p>
                        </div>
                    </div>
                `;
                
                return fetch(`/room/${username}/users`);
            })
            .then(response => response.json())
            .then(usersData => {
                if (usersData.error) throw new Error(usersData.error);
                
                userCount.textContent = `${formatNumber(usersData.users.length)} viewers in chat`;
                
                if (usersData.users.length > 0) {
                    userGrid.innerHTML = usersData.users.map(user => `
                        <div class="user-card">
                            <div class="user-icon">👤</div>
                            <div class="user-name">${user.username}</div>
                            <div class="user-gender">${user.gender || ''}</div>
                        </div>
                    `).join('');
                } else {
                    userGrid.innerHTML = '<div>No users in chat</div>';
                }
                
                // Load clips for this user
                loadClips(username);
            })
            .catch(e => {
                console.error("Error loading details:", e);
                panelInfo.innerHTML = `<p class="error">Error loading room data: ${e.message}</p>`;
            });
        
        box.scrollIntoView({ behavior: 'smooth' });
    }
    
    function closeDetails() {
        const box = document.getElementById("detail-box");
        const videoFrame = document.getElementById("video-frame");
        box.style.display = "none";
        videoFrame.src = "";
        
        // Stop any ongoing recording
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            stopRecording();
        }
    }
    
    // Navigation functions
    function updateNavigationButtons() {
        const prevBtn = document.querySelector('.nav-button.prev');
        const nextBtn = document.querySelector('.nav-button.next');
        
        prevBtn.disabled = currentFavIndex <= 0;
        nextBtn.disabled = currentFavIndex >= favRooms.length - 1;
    }
    
    function navigateFavorite(direction) {
        currentFavIndex += direction;
        currentFavIndex = Math.max(0, Math.min(currentFavIndex, favRooms.length - 1));
        loadDetails(favRooms[currentFavIndex]);
        updateNavigationButtons();
    }
    
    // Utility functions
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }
    
    function searchTags() {
        const searchTerm = document.getElementById("tag-search").value.toLowerCase();
        document.querySelectorAll(".filter-tag").forEach(tag => {
            tag.style.display = tag.textContent.toLowerCase().includes(searchTerm) ? "block" : "none";
        });
    }
    
    function toggleTagFilter(tag) {
        const tagElements = document.querySelectorAll(".filter-tag");
        
        tagElements.forEach(el => {
            if (el.textContent === tag) {
                if (activeTags.has(tag)) {
                    activeTags.delete(tag);
                    el.classList.remove("active");
                } else {
                    activeTags.add(tag);
                    el.classList.add("active");
                }
            }
        });
        
        filterRooms();
        savePreferences();
    }
    
    function searchBroadcasters() {
        const searchTerm = document.getElementById("broadcaster-search").value.toLowerCase();
        document.querySelectorAll(".room-card").forEach(room => {
            const username = room.dataset.username.toLowerCase();
            room.style.display = username.includes(searchTerm) ? "block" : "none";
        });
    }
    
    // Theme functions
    function toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        savePreferences();
    }
    
    // Notes functions
    function showNotesModal(username) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Notes for ${username}</h3>
                <textarea id="note-text">${notes[username] || ''}</textarea>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button onclick="saveNote('${username}')">Save</button>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    function saveNote(username) {
        const text = document.getElementById('note-text').value;
        notes[username] = text;
        saveNotes();
        document.querySelector('.modal').remove();
        if (currentUsername === username) {
            document.querySelector('.user-note p').textContent = text || 'No note yet';
        }
    }
    
    // Import/Export functions
    function exportFavorites() {
        const data = {
            favorites: Array.from(favorites),
            notes: notes
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'charmlive-data.json';
        a.click();
    }
    
    function importFavorites(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                if (data.favorites) {
                    favorites = new Set(data.favorites);
                    saveFavorites();
                    updateFavoriteButtons();
                    filterFavorites();
                }
                if (data.notes) {
                    notes = data.notes;
                    saveNotes();
                }
                showNotification('Data imported successfully!');
            } catch (error) {
                showNotification('Error importing data: Invalid file format', true);
                console.error('Import error:', error);
            }
        };
        reader.readAsText(file);
    }
    
    // Real-time updates
    function startUpdates() {
        updateInterval = setInterval(() => {
            fetch('/api/refresh')
                .then(response => response.json())
                .then(data => {
                    updateRoomData(data.rooms);
                    checkFavoritesOnline(data.online_favorites);
                })
                .catch(error => console.error('Update error:', error));
        }, 60000); // Update every 60 seconds
    }
    
    function stopUpdates() {
        clearInterval(updateInterval);
    }
    
    function updateRoomData(rooms) {
        // This would update the room data in a real implementation
        console.log('Room data updated', rooms);
    }
    
    function checkFavoritesOnline(onlineFavorites) {
        if (Notification.permission === 'granted') {
            onlineFavorites.forEach(username => {
                if (!lastOnlineStatus[username]) {
                    new Notification(`${username} is now online!`, {
                        body: 'Click to view their stream',
                        icon: 'https://i.imgur.com/3Zx5XeI.png'
                    });
                }
                lastOnlineStatus[username] = true;
            });
            
            // Update offline status
            Object.keys(lastOnlineStatus).forEach(username => {
                if (!onlineFavorites.includes(username)) {
                    lastOnlineStatus[username] = false;
                }
            });
        }
    }
    
    // Performance optimizations
    function initializeIntersectionObserver() {
        if ('IntersectionObserver' in window) {
            const lazyImages = document.querySelectorAll('img.lazy');
            const lazyImageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const lazyImage = entry.target;
                        lazyImage.src = lazyImage.src;
                        lazyImage.classList.remove('lazy');
                        lazyImageObserver.unobserve(lazyImage);
                    }
                });
            });
            
            lazyImages.forEach(lazyImage => {
                lazyImageObserver.observe(lazyImage);
            });
        }
    }
    
    // Notification permission
    function requestNotificationPermission() {
        if ('Notification' in window && Notification.permission !== 'granted') {
            Notification.requestPermission();
        }
    }
    
    // Show notification
    function showNotification(message, isError = false) {
        const notification = document.createElement('div');
        notification.className = `notification ${isError ? 'error' : ''}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
    
    // Keyboard shortcuts
    function handleKeyDown(e) {
        const detailBox = document.getElementById("detail-box");
        if (detailBox.style.display === "block") {
            if (e.key === 'Escape') {
                closeDetails();
            }
            if (document.getElementById("favorites-filter").value === 'favorites') {
                if (e.key === 'ArrowLeft') {
                    navigateFavorite(-1);
                }
                if (e.key === 'ArrowRight') {
                    navigateFavorite(1);
                }
            }
        }
    }
    
    // Clip recording functions
    async function startRecording() {
        try {
            // Request screen capture
            stream = await navigator.mediaDevices.getDisplayMedia({
                video: { mediaSource: "screen" },
                audio: true
            });
            
            // Create media recorder
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'video/webm; codecs=vp9,opus'
            });
            
            // Event handler for data available
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };
            
            // Event handler for stopping
            mediaRecorder.onstop = () => {
                // Create a blob from the recorded chunks
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                saveClip(blob);
                recordedChunks = [];
            };
            
            // Start recording
            mediaRecorder.start(1000); // Collect data every second
            
            // Update UI
            document.getElementById('record-button').disabled = true;
            document.getElementById('recording-status').style.display = 'flex';
            recordingTimeLeft = 30;
            updateCountdown();
            
            // Stop after 30 seconds
            recordingInterval = setInterval(() => {
                recordingTimeLeft--;
                updateCountdown();
                
                if (recordingTimeLeft <= 0) {
                    stopRecording();
                }
            }, 1000);
            
        } catch (error) {
            console.error('Error starting recording:', error);
            showNotification('Could not start recording: ' + error.message, true);
        }
    }
    
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            clearInterval(recordingInterval);
            resetRecordingUI();
            
            // Stop all tracks
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        }
    }
    
    function resetRecordingUI() {
        document.getElementById('record-button').disabled = false;
        document.getElementById('recording-status').style.display = 'none';
        recordingTimeLeft = 30;
    }
    
    function updateCountdown() {
        document.getElementById('countdown').textContent = `${recordingTimeLeft}s`;
    }
    
    function saveClip(blob) {
        // Convert blob to base64 for storage
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = function() {
            const base64data = reader.result;
            
            // Save clip to server
            fetch('/save_clip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: currentUsername,
                    clipData: base64data
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Clip saved successfully!');
                    loadClips(currentUsername);
                } else {
                    showNotification('Error saving clip: ' + data.error, true);
                }
            })
            .catch(error => {
                console.error('Error saving clip:', error);
                showNotification('Error saving clip', true);
            });
        };
    }
    
    function loadClips(username) {
        fetch(`/get_clips/${username}`)
            .then(response => response.json())
            .then(clips => {
                const clipsList = document.getElementById('clips-list');
                
                if (clips.length === 0) {
                    clipsList.innerHTML = '<div class="no-clips">No clips recorded yet.</div>';
                    return;
                }
                
                clipsList.innerHTML = clips.map(clip => `
                    <div class="clip-item">
                        <video width="100%" controls>
                            <source src="${clip.data}" type="video/webm">
                            Your browser does not support the video tag.
                        </video>
                        <div class="clip-info">
                            <span>${new Date(clip.timestamp).toLocaleString()}</span>
                            <button class="delete-clip" onclick="deleteClip('${clip.id}')">Delete</button>
                        </div>
                    </div>
                `).join('');
            })
            .catch(error => {
                console.error('Error loading clips:', error);
            });
    }
    
    function deleteClip(clipId) {
        if (!confirm('Are you sure you want to delete this clip?')) return;
        
        fetch(`/delete_clip/${clipId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Clip deleted successfully!');
                    loadClips(currentUsername);
                } else {
                    showNotification('Error deleting clip: ' + data.error, true);
                }
            })
            .catch(error => {
                console.error('Error deleting clip:', error);
                showNotification('Error deleting clip', true);
            });
    }
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        // Clear all intervals
        Object.values(hoverRefreshIntervals).forEach(interval => {
            clearInterval(interval);
        });
        clearInterval(globalRefreshInterval);
        
        // Stop any ongoing recording
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            stopRecording();
        }
    });
    </script>
</body>
</html>
"""

API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://chaturbate.com/"
}

@app.route("/")
def index():
    try:
        # Try to load from cache first
        cache = load_data(ROOM_CACHE_FILE, {})
        if cache and cache.get('expires', 0) > time.time():
            rooms = cache.get('rooms', [])
        else:
            response = '''{"rooms":[{"display_age":null,"gender":"f","location":"Washington, United States","current_show":"public","username":"avaowenss","tags":["18","new","innocent"],"is_new":true,"num_users":3533,"num_followers":16869,"start_dt_utc":"2025-09-11T04:16:55.785776+00:00","country":"US","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"new","is_following":false,"source_name":"df","start_timestamp":1757564215,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/avaowenss.jpg?1757590320","subject":"ride pillow <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/innocent\/\">#innocent<\/a> [720 tokens remaining]"},{"display_age":29,"gender":"f","location":"Sugarcountry","current_show":"public","username":"lili_and_niki","tags":["bigboobs","bigass","lovense","cum","tease"],"is_new":false,"num_users":3323,"num_followers":739172,"start_dt_utc":"2025-09-11T07:24:04.633493+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757575444,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/lili_and_niki.jpg?1757590320","subject":"\ud83d\udc95be my lover\ud83d\udc95lovense vulse <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/tease\/\">#tease<\/a>"},{"display_age":22,"gender":"f","location":"in the moment","current_show":"public","username":"ms_dira","tags":["feet","tease","hairy","hairyarmpits"],"is_new":false,"num_users":2108,"num_followers":322798,"start_dt_utc":"2025-09-11T09:12:29.616087+00:00","country":"","has_password":false,"private_price":360,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757581949,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/ms_dira.jpg?1757590320","subject":"<a href=\"\/tag\/feet\/\">#feet<\/a> <a href=\"\/tag\/tease\/\">#tease<\/a> <a href=\"\/tag\/hairy\/\">#hairy<\/a> <a href=\"\/tag\/hairyarmpits\/\">#hairyarmpits<\/a>  \/\/ goal \u301c make my nipples hard close up [1302 tokens left] \/\/ epic goal \u301c ticket show [5935 tokens left]"},{"display_age":99,"gender":"f","location":"Planet Earth","current_show":"public","username":"mysat","tags":["lovense","18","teen","anal","bigass"],"is_new":false,"num_users":2455,"num_followers":402019,"start_dt_utc":"2025-09-11T09:19:21.264785+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":12,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757582361,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/mysat.jpg?1757590320","subject":"goal: play pussy [564 tokens remaining] my fav pattern - 104\/160\/207! welcome to my room! <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a>"},{"display_age":38,"gender":"c","location":"Hungary","current_show":"public","username":"davids_angelsxxx","tags":["threesome","deepthroat","bigcock","milf","feet"],"is_new":false,"num_users":2128,"num_followers":493242,"start_dt_utc":"2025-09-11T09:32:22.369149+00:00","country":"","has_password":false,"private_price":240,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757583142,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/davids_angelsxxx.jpg?1757590320","subject":"play with us! 58,111,666,1111 <a href=\"\/tag\/threesome\/\">#threesome<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a> <a href=\"\/tag\/bigcock\/\">#bigcock<\/a> <a href=\"\/tag\/milf\/\">#milf<\/a> <a href=\"\/tag\/feet\/\">#feet<\/a>"},{"display_age":null,"gender":"f","location":"one day i will live on island in the pacific ocean","current_show":"public","username":"honey_sunshine","tags":["squirt","bigass","teen","braces","pawg"],"is_new":false,"num_users":1874,"num_followers":801578,"start_dt_utc":"2025-09-11T09:09:47.342644+00:00","country":"","has_password":false,"private_price":240,"spy_show_price":54,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757581787,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/honey_sunshine.jpg?1757590320","subject":"squirt! tip99\/169\/222\/500\/1000 and i cum like ocean [1000 tokens left] <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/braces\/\">#braces<\/a> <a href=\"\/tag\/pawg\/\">#pawg<\/a>"},{"display_age":33,"gender":"f","location":"Living in Spain","current_show":"public","username":"miss_juliaa","tags":["lush","blonde","new","squirt","cum"],"is_new":false,"num_users":1725,"num_followers":931021,"start_dt_utc":"2025-09-11T10:36:46.308315+00:00","country":"","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587006,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/miss_juliaa.jpg?1757590320","subject":"wet today? 1222 tks panties,550tks snap,2200 tks snap and 180full videos,see tipmenu first\/  links on screen <a href=\"\/tag\/lush\/\">#lush<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a> #toys"},{"display_age":26,"gender":"f","location":":)","current_show":"public","username":"elaanna","tags":["squirt","cum","naked","young","lovense"],"is_new":false,"num_users":1705,"num_followers":972088,"start_dt_utc":"2025-09-11T06:36:13.219610+00:00","country":"","has_password":false,"private_price":240,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757572573,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/elaanna.jpg?1757590320","subject":"<a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/naked\/\">#naked<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> #lush"},{"display_age":null,"gender":"m","location":"United States","current_show":"public","username":"vj48826","tags":["c2c","free"],"is_new":false,"num_users":16,"num_followers":166,"start_dt_utc":"2025-09-11T11:00:48.442139+00:00","country":"US","has_password":false,"private_price":60,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"promoted","source_name":"pr","source_position":1,"is_following":false,"start_timestamp":1757588448,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/vj48826.jpg?1757590320","subject":"#freec2c <a href=\"\/tag\/c2c\/\">#c2c<\/a> <a href=\"\/tag\/free\/\">#free<\/a>"},{"display_age":23,"gender":"c","location":"looking for good Mod","current_show":"public","username":"out_lust","tags":["bigtits","anal","threesome","deepthroat","facial"],"is_new":false,"num_users":2028,"num_followers":291377,"start_dt_utc":"2025-09-11T10:26:02.643946+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757586362,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/out_lust.jpg?1757590320","subject":"goal: fuck this tight pussy [168 tokens left] <a href=\"\/tag\/bigtits\/\">#bigtits<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/threesome\/\">#threesome<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a> <a href=\"\/tag\/facial\/\">#facial<\/a>"},{"display_age":null,"gender":"f","location":"Europe","current_show":"public","username":"thatgirl___","tags":["tease","bigboobs","cute","lovense","natural"],"is_new":false,"num_users":1665,"num_followers":545285,"start_dt_utc":"2025-09-11T07:52:24.077813+00:00","country":"","has_password":false,"private_price":240,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757577144,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/thatgirl___.jpg?1757590320","subject":"i am back, my friends! i missed you so much! let`s have some fun tonight? my patterns - 111\/333\/555\/1111 &lt;3 - goal: full naked [5786 tokens left] <a href=\"\/tag\/tease\/\">#tease<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/cute\/\">#cute<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a>"},{"display_age":20,"gender":"f","location":"Cat's Lair","current_show":"public","username":"lissa_meooow","tags":["lovense","shy","blonde","teen","bigboobs"],"is_new":false,"num_users":1337,"num_followers":309587,"start_dt_utc":"2025-09-11T05:57:05.828022+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757570225,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/lissa_meooow.jpg?1757590320","subject":"hi! i\u2019ll do pvts before break and at end of stream only \ud83d\udc97 - goal reached! <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a>"},{"display_age":27,"gender":"f","location":"all women from venus! and I am no exception","current_show":"public","username":"oxxme","tags":[],"is_new":false,"num_users":1248,"num_followers":624720,"start_dt_utc":"2025-09-11T09:00:16.914636+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757581216,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/oxxme.jpg?1757590320","subject":"undress me\u2764\ufe0ftry my favorite vibes 40,99,101, 131,555 \u2764\ufe0f [33 tokens remaining]"},{"display_age":37,"gender":"c","location":"chaturbate","current_show":"public","username":"sex_space","tags":["bigboobs","bigass","milf","mom","bbw"],"is_new":false,"num_users":1236,"num_followers":158118,"start_dt_utc":"2025-09-11T09:22:34.386516+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":54,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757582554,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sex_space.jpg?1757590320","subject":"shh...my stepson is here\u2764\ufe0froll&#x27;dice-111\u2764\ufe0fsquirt-567\u2764\ufe0ftoypatterns-99\/111\/222\/444\u2764\ufe0f <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/milf\/\">#milf<\/a> <a href=\"\/tag\/mom\/\">#mom<\/a> <a href=\"\/tag\/bbw\/\">#bbw<\/a> #lovense #lush -- current goal: naked front him"},{"display_age":null,"gender":"f","location":"unknown","current_show":"public","username":"kenziesmithh","tags":["new","feet","blonde","18","innocent"],"is_new":false,"num_users":812,"num_followers":72024,"start_dt_utc":"2025-09-11T04:16:58.848964+00:00","country":"US","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757564218,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/kenziesmithh.jpg?1757590320","subject":"doggyyyy <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/feet\/\">#feet<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/innocent\/\">#innocent<\/a> [332 tokens remaining]"},{"display_age":99,"gender":"f","location":"Follow me!! :))","current_show":"public","username":"nyconik","tags":["18","lovense"],"is_new":false,"num_users":1584,"num_followers":662836,"start_dt_utc":"2025-09-11T09:11:59.005703+00:00","country":"RO","has_password":false,"private_price":180,"spy_show_price":180,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757581919,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/nyconik.jpg?1757590320","subject":"shhhh cum show   :)) device that vibrates longer at your tips and gives me pleasures <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a>"},{"display_age":22,"gender":"c","location":"???","current_show":"public","username":"loossers","tags":["teen","18","lovense","bigboobs","deepthroat"],"is_new":false,"num_users":1520,"num_followers":180183,"start_dt_utc":"2025-09-11T10:25:22.845743+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757586322,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/loossers.jpg?1757590320","subject":"rubbing wet pussy on cock [178 tokens left] <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a>"},{"display_age":25,"gender":"f","location":"Nowhere","current_show":"public","username":"kerelai","tags":["lovense","bigboobs","bigass","cumshow","asian"],"is_new":false,"num_users":1336,"num_followers":626265,"start_dt_utc":"2025-09-11T09:35:05.165501+00:00","country":"","has_password":false,"private_price":240,"spy_show_price":360,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757583305,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/kerelai.jpg?1757590320","subject":"wet my panties tip 111\/333\/1234 \u2764\ufe0f - goal: dildo in pussy [9760 tokens left] <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/cumshow\/\">#cumshow<\/a> <a href=\"\/tag\/asian\/\">#asian<\/a>"},{"display_age":25,"gender":"f","location":"Born in France, Live in Australia now","current_show":"public","username":"livecleo","tags":["bigass","bigboob","lovense","pantyhose","squirt"],"is_new":false,"num_users":989,"num_followers":574808,"start_dt_utc":"2025-09-11T08:30:01.115200+00:00","country":"AU","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757579401,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/livecleo.jpg?1757590320","subject":"misscleo french class! who will be my naughtiest boy? <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/bigboob\/\">#bigboob<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/pantyhose\/\">#pantyhose<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a>"},{"display_age":18,"gender":"c","location":"PM","current_show":"public","username":"misska__","tags":["new","skinny","tease","young","petite"],"is_new":true,"num_users":1313,"num_followers":6291,"start_dt_utc":"2025-09-11T08:03:46.991900+00:00","country":"","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"new","is_following":false,"source_name":"df","start_timestamp":1757577826,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/misska__.jpg?1757590320","subject":"hey! (\u3002\u30fb\u03c9\u30fb\u3002) that&#x27;s my third day here!  \/\/ goal: camel toe in doggy position close up [263 tokens left] \/\/ epic goal: stroking each other&#x27;s panties [663 tokens left] <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/tease\/\">#tease<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/petite\/\">#petite<\/a>"},{"display_age":19,"gender":"f","location":"NARNIA \u2764\ufe0f","current_show":"public","username":"shena_nomy","tags":[],"is_new":false,"num_users":1228,"num_followers":742613,"start_dt_utc":"2025-09-11T09:50:08.681614+00:00","country":"","has_password":false,"private_price":12,"spy_show_price":6,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757584208,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/shena_nomy.jpg?1757590320","subject":"lick your cock [193 tokens left]"},{"display_age":18,"gender":"c","location":"your screen","current_show":"public","username":"ebangelion","tags":["teen","new","sex","bigdick","blonde"],"is_new":false,"num_users":1017,"num_followers":357520,"start_dt_utc":"2025-09-11T10:37:15.620004+00:00","country":"","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587035,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/ebangelion.jpg?1757590320","subject":"hello guys! - goal: sex and cumshow in ticket [2802 tokens left] <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/sex\/\">#sex<\/a> <a href=\"\/tag\/bigdick\/\">#bigdick<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a>"},{"display_age":null,"gender":"c","location":"\ud83d\udc9c\ud83d\udc9c\ud83d\udc9cearth \ud83d\udc9c\ud83d\udc9c\ud83d\udc9cwhere your dreams come true\ud83d\udc9c\ud83d\udc9c\ud83d\udc9c","current_show":"public","username":"_timeless_paradox","tags":["fingers"],"is_new":false,"num_users":816,"num_followers":1259857,"start_dt_utc":"2025-09-11T09:23:37.591240+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757582617,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/_timeless_paradox.jpg?1757590320","subject":"<a href=\"\/tag\/fingers\/\">#fingers<\/a> in anal [676 tokens remaining]"},{"display_age":19,"gender":"f","location":"California","current_show":"public","username":"lynnalltop","tags":["new","young","18","redhead","shy"],"is_new":false,"num_users":986,"num_followers":263305,"start_dt_utc":"2025-09-11T04:14:03.517955+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757564043,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/lynnalltop.jpg?1757590320","subject":"my name is natasha! i&#x27;m a <a href=\"\/tag\/new\/\">#new<\/a> and <a href=\"\/tag\/young\/\">#young<\/a> model on cb <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/redhead\/\">#redhead<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> goal:  lush inside, i need this for best level of pleasure  [1714 tokens remaining]"},{"display_age":18,"gender":"s","location":"Antioquia, Colombia","current_show":"public","username":"charlie_eusse","tags":["anal","bigcock","trans","18","femboy"],"is_new":false,"num_users":743,"num_followers":71757,"start_dt_utc":"2025-09-11T07:52:33.397819+00:00","country":"CO","has_password":false,"private_price":90,"spy_show_price":12,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757577153,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/charlie_eusse.jpg?1757590320","subject":"current goal: my hot cum at 3000 tokens -- next goal: show sexy dildo -- sex show at final goal <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/bigcock\/\">#bigcock<\/a> <a href=\"\/tag\/trans\/\">#trans<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/femboy\/\">#femboy<\/a>"},{"display_age":19,"gender":"f","location":"Slovenia","current_show":"public","username":"eva_zill_blossom","tags":["shy","smalltits","18","teen","new"],"is_new":false,"num_users":768,"num_followers":80288,"start_dt_utc":"2025-09-11T10:33:50.616584+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757586830,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/eva_zill_blossom.jpg?1757590320","subject":"goal:i&#x27;m already wet, control toy for the last tipper to drive me crazy! i&#x27;m eva, a little <a href=\"\/tag\/shy\/\">#shy<\/a> about my <a href=\"\/tag\/smalltits\/\">#smalltits<\/a> because i&#x27;m <a href=\"\/tag\/18\/\">#18<\/a> y.o i am <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/new\/\">#new<\/a> girl here [156 tokens remaining]"},{"display_age":18,"gender":"f","location":"Venice","current_show":"public","username":"emmiemurray","tags":["18","shy","new","teen","blonde"],"is_new":false,"num_users":878,"num_followers":51208,"start_dt_utc":"2025-09-11T06:11:02.130014+00:00","country":"","has_password":false,"private_price":6,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757571062,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/emmiemurray.jpg?1757590320","subject":"g:  remove hands and play with my bare breast \/ call me aurora, i&#x27;m from venice, i&#x27;m <a href=\"\/tag\/18\/\">#18<\/a> y.o. will you be my friend? <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> [524 tokens remaining]"},{"display_age":null,"gender":"f","location":"My windows are tinted ! NOT A PUBLIC PLACE","current_show":"public","username":"sassyt33n","tags":["lovense","anal","teen","boobs","ass"],"is_new":false,"num_users":653,"num_followers":700864,"start_dt_utc":"2025-09-11T08:37:20.654870+00:00","country":"RO","has_password":false,"private_price":180,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757579840,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sassyt33n.jpg?1757590320","subject":"make me cum with 222 333 444 1111 500 ! <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/boobs\/\">#boobs<\/a> <a href=\"\/tag\/ass\/\">#ass<\/a> - multi-goal :  cum show <a href=\"\/tag\/lovense\/\">#lovense<\/a> #feet <a href=\"\/tag\/teen\/\">#teen<\/a> #squirt <a href=\"\/tag\/anal\/\">#anal<\/a>"},{"display_age":19,"gender":"f","location":"Vienna, Austria","current_show":"public","username":"yess_kiki","tags":["new","shy","bigboobs","heels","cute"],"is_new":false,"num_users":885,"num_followers":101562,"start_dt_utc":"2025-09-11T08:21:04.397105+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757578864,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/yess_kiki.jpg?1757590320","subject":"goal: spray water and hot teasing with my boobs &lt;3  || &quot;my first excl pvt in my life. pre-tip 20 000tk&quot; i&#x27;m <a href=\"\/tag\/new\/\">#new<\/a> here and a little <a href=\"\/tag\/shy\/\">#shy<\/a>!!! <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/heels\/\">#heels<\/a> <a href=\"\/tag\/cute\/\">#cute<\/a> [116 tokens remaining]"},{"display_age":21,"gender":"f","location":"in wonderland \u2728","current_show":"public","username":"marce_algara","tags":["lovense","new","latina","squirt","asian"],"is_new":false,"num_users":904,"num_followers":229128,"start_dt_utc":"2025-09-11T09:20:06.899619+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757582406,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/marce_algara.jpg?1757590320","subject":"ride dildo <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/latina\/\">#latina<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/asian\/\">#asian<\/a> [631 tokens remaining]"},{"display_age":99,"gender":"f","location":"In front of you :P","current_show":"public","username":"sweet_ary","tags":["boobs","naked","pussy","snap4life","feet"],"is_new":false,"num_users":456,"num_followers":1203948,"start_dt_utc":"2025-09-11T11:00:53.182688+00:00","country":"","has_password":false,"private_price":180,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588453,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sweet_ary.jpg?1757590320","subject":"make me feel good to cum\/30 min naked\u2764\ufe0f\/tipmenu for more 200 <a href=\"\/tag\/boobs\/\">#boobs<\/a>\/ 1111 <a href=\"\/tag\/naked\/\">#naked<\/a>\/ 605 <a href=\"\/tag\/pussy\/\">#pussy<\/a>\/ 555 <a href=\"\/tag\/snap4life\/\">#snap4life<\/a>\/ 110 <a href=\"\/tag\/feet\/\">#feet<\/a>\/ 322 cream on boobs or #ass\/ 505 #doggy #lovense [next tip needed: 1 tokens]"},{"display_age":20,"gender":"f","location":"in your mind","current_show":"public","username":"xenomy","tags":["cosplay","cum","squirt","mistress","skinny"],"is_new":false,"num_users":521,"num_followers":401414,"start_dt_utc":"2025-09-11T06:20:14.362053+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757571614,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/xenomy.jpg?1757590320","subject":"deepthroat and eye contact(\u25cf&#x27;\u25e1&#x27;\u25cf) [101 tokens left] <a href=\"\/tag\/cosplay\/\">#cosplay<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a>  <a href=\"\/tag\/mistress\/\">#mistress<\/a>  <a href=\"\/tag\/skinny\/\">#skinny<\/a>"},{"display_age":19,"gender":"f","location":"Prague, Czechia","current_show":"public","username":"kissiekat","tags":["18","shy","new","teen","bigboobs"],"is_new":false,"num_users":806,"num_followers":79688,"start_dt_utc":"2025-09-11T07:08:14.852973+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757574494,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/kissiekat.jpg?1757590320","subject":"goal: drops of water running down my boobs to my belly button [555 tokens remaining] hi i am lola \u25d5\u203f\u25d5 welcome to my show <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a>"},{"display_age":19,"gender":"f","location":"Estonia","current_show":"public","username":"bellacle","tags":["teen","shy","bigboobs","blowjob","sexy"],"is_new":false,"num_users":589,"num_followers":349660,"start_dt_utc":"2025-09-11T07:27:53.302393+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757575673,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/bellacle.jpg?1757590320","subject":"goal:  pull down the top part of my bodysuit  \/\/  <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/blowjob\/\">#blowjob<\/a> <a href=\"\/tag\/sexy\/\">#sexy<\/a> [140 tokens remaining]"},{"display_age":22,"gender":"f","location":"Japan","current_show":"public","username":"hi_miki","tags":["asian","anal","squirt","lovense","fuckmachine"],"is_new":false,"num_users":489,"num_followers":494911,"start_dt_utc":"2025-09-11T10:41:51.540130+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587311,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/hi_miki.jpg?1757590320","subject":"lets make me squirt - goal is : fountain squirt <a href=\"\/tag\/asian\/\">#asian<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/fuckmachine\/\">#fuckmachine<\/a>"},{"display_age":27,"gender":"f","location":"United Kingdom","current_show":"public","username":"babesgowild","tags":["heels","findom","squirt","anal","bigboob"],"is_new":false,"num_users":473,"num_followers":635815,"start_dt_utc":"2025-09-11T10:56:06.879507+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588166,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/babesgowild.jpg?1757590320","subject":"i dare you not to vibe me! i m at work! nver use 101\/202\/303\/404 that drive me crazy! cum show <a href=\"\/tag\/heels\/\">#heels<\/a> <a href=\"\/tag\/findom\/\">#findom<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/bigboob\/\">#bigboob<\/a> #bigass [2885 tokens left]"},{"display_age":null,"gender":"f","location":"the void","current_show":"public","username":"wyvernwench","tags":[],"is_new":false,"num_users":410,"num_followers":63769,"start_dt_utc":"2025-09-11T05:45:37.488696+00:00","country":"","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757569537,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/wyvernwench.jpg?1757590320","subject":"wyvernwench&#x27;s room"},{"display_age":null,"gender":"f","location":"UK- England (don\u2019t ask where pls)","current_show":"public","username":"daddiesgirl69_","tags":["british","smalltits","bigass","squirt","pantyhose"],"is_new":false,"num_users":624,"num_followers":364979,"start_dt_utc":"2025-09-11T09:37:07.407880+00:00","country":"GB","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757583427,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/daddiesgirl69_.jpg?1757590320","subject":"goal: let&#x27;s squirt! \ud83d\udca6  48, 100 and 190 tks are my  fav \ud83d\ude08 |  new videos in bio!   <a href=\"\/tag\/british\/\">#british<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/pantyhose\/\">#pantyhose<\/a> [1831 tokens remaining]"},{"display_age":null,"gender":"f","location":"in your fantasies","current_show":"public","username":"my_mia_","tags":["18","teen","shy","skinny","tease"],"is_new":false,"num_users":513,"num_followers":144647,"start_dt_utc":"2025-09-11T06:53:48.437080+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757573628,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/my_mia_.jpg?1757590320","subject":"goal: top off, bra on [222 left]  \ud83e\udd8b epic goal: china trip [42314 left] \ud83e\udd8b <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/tease\/\">#tease<\/a>"},{"display_age":24,"gender":"f","location":"USA","current_show":"public","username":"rosyemily","tags":["bigboobs","18","teen","daddysgirl","squirt"],"is_new":false,"num_users":599,"num_followers":712190,"start_dt_utc":"2025-09-11T10:52:51.396495+00:00","country":"","has_password":false,"private_price":180,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587971,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/rosyemily.jpg?1757590320","subject":"<a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/daddysgirl\/\">#daddysgirl<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> -- current goal: \ud83c\udf38play with pussy and touch boobs once countdown reaches zero -- next goal: \ud83c\udf38domi  control 7minutes [57 tokens to goal]"},{"display_age":null,"gender":"f","location":"Dubai, United Arab Emirates","current_show":"public","username":"ren_esma","tags":["asian","18","squirt","new","smalltits"],"is_new":true,"num_users":674,"num_followers":14616,"start_dt_utc":"2025-09-11T02:51:02.144261+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":12,"is_gaming":false,"is_age_verified":true,"label":"new","is_following":false,"source_name":"df","start_timestamp":1757559062,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/ren_esma.jpg?1757590320","subject":"goal reached!  thanks to all tippers! don&#x27;t forget to thumbs up!&lt;3 <a href=\"\/tag\/asian\/\">#asian<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a>"},{"display_age":null,"gender":"f","location":"Lalalend","current_show":"public","username":"yourmaylien","tags":["asian","natural","shy","young","daddysgirl"],"is_new":false,"num_users":665,"num_followers":68884,"start_dt_utc":"2025-09-11T06:02:05.610863+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":6,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757570525,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/yourmaylien.jpg?1757590320","subject":"25\/38\/100\/120\/160\/200 \/\/ all goals completed!  thanks to all tippers! \/\/ epic goal: squirt [1426 tokens left] <a href=\"\/tag\/asian\/\">#asian<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/daddysgirl\/\">#daddysgirl<\/a>"},{"display_age":41,"gender":"f","location":"UK","current_show":"public","username":"english_rose__","tags":["british","milf","mature","bigboobs","lovense"],"is_new":false,"num_users":488,"num_followers":705005,"start_dt_utc":"2025-09-11T07:41:09.098010+00:00","country":"GB","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757576469,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/english_rose__.jpg?1757590320","subject":"<a href=\"\/tag\/british\/\">#british<\/a> <a href=\"\/tag\/milf\/\">#milf<\/a> <a href=\"\/tag\/mature\/\">#mature<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> 88 is my fav!"},{"display_age":null,"gender":"c","location":"On your Screen","current_show":"public","username":"naughtystyle69","tags":["lovense","smalltits","young","blonde","squirt"],"is_new":false,"num_users":787,"num_followers":208395,"start_dt_utc":"2025-09-11T11:10:06.346491+00:00","country":"","has_password":false,"private_price":72,"spy_show_price":54,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757589006,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/naughtystyle69.jpg?1757590320","subject":"cream pie@goal\u2b50 pvt open \/ fav levels\u2764\ufe0f 111\/222\/444 [743 tokens left] <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a>"},{"display_age":null,"gender":"f","location":"your dreams","current_show":"public","username":"doll_lexi","tags":["bigboobs","anal","squirt","lush","brunette"],"is_new":false,"num_users":317,"num_followers":356858,"start_dt_utc":"2025-09-11T10:37:25.635289+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587045,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/doll_lexi.jpg?1757590320","subject":"my fav vibes 98 \/114\/115\/555 | @goal naked | <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/lush\/\">#lush<\/a> <a href=\"\/tag\/brunette\/\">#brunette<\/a> |"},{"display_age":20,"gender":"c","location":"norte de santander","current_show":"public","username":"sexy_hot_friends_","tags":["new","assfuck","cumshow","squirtshow","lesbian"],"is_new":false,"num_users":779,"num_followers":101212,"start_dt_utc":"2025-09-11T05:02:12.905018+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":12,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757566932,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sexy_hot_friends_.jpg?1757590320","subject":"goal: lick tits welcome to my room! <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/assfuck\/\">#assfuck<\/a> <a href=\"\/tag\/cumshow\/\">#cumshow<\/a> <a href=\"\/tag\/squirtshow\/\">#squirtshow<\/a> <a href=\"\/tag\/lesbian\/\">#lesbian<\/a> lick balls : 99"},{"display_age":24,"gender":"f","location":"Colombia","current_show":"public","username":"itsbellax","tags":["deepthroat","bigboobs","feet","pantyhose","18"],"is_new":false,"num_users":565,"num_followers":184679,"start_dt_utc":"2025-09-11T09:14:06.232832+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757582046,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/itsbellax.jpg?1757590320","subject":"goal: fuck boobs [39 tokens remaining] welcome to my room! <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/feet\/\">#feet<\/a> <a href=\"\/tag\/pantyhose\/\">#pantyhose<\/a> <a href=\"\/tag\/18\/\">#18<\/a>"},{"display_age":null,"gender":"f","location":"\ud835\udc08\ud835\udc27 \ud835\udc1a \ud835\udc1c\ud835\udc28\ud835\udc33\ud835\udc32 \ud835\udc21\ud835\udc22\ud835\udc1d\ud835\udc1e\ud835\udc1a\ud835\udc30\ud835\udc1a\ud835\udc32 \ud835\udc23\ud835\udc2e\ud835\udc2c\ud835\udc2d \ud835\udc1f\ud835\udc28\ud835\udc2b \ud835\udc2e\ud835\udc2c \ud83d\udecb\ufe0f","current_show":"public","username":"chloe_ri","tags":["bigboobs","heels","stockings","lovense","feet"],"is_new":false,"num_users":548,"num_followers":139888,"start_dt_utc":"2025-09-11T10:39:29.615653+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587169,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/chloe_ri.jpg?1757590320","subject":"\ud83d\udc60 \/\/ goal: boobs tease at 1k, drool on at goal\ud83d\udd25 \/\/ type \/menu to play with me! <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/heels\/\">#heels<\/a> <a href=\"\/tag\/stockings\/\">#stockings<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/feet\/\">#feet<\/a>"},{"display_age":22,"gender":"f","location":"Russia","current_show":"public","username":"wellicaren","tags":["braces","squirt","blonde","bigass","stockings"],"is_new":false,"num_users":643,"num_followers":206559,"start_dt_utc":"2025-09-11T09:55:00.809486+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757584500,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/wellicaren.jpg?1757590320","subject":"<a href=\"\/tag\/braces\/\">#braces<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/stockings\/\">#stockings<\/a>"},{"display_age":19,"gender":"s","location":"Riga, Latvia","current_show":"public","username":"sweet_reverie","tags":["skinny","bigcock","trans","teen","femboy"],"is_new":false,"num_users":548,"num_followers":33044,"start_dt_utc":"2025-09-11T08:55:19.364334+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757580919,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sweet_reverie.jpg?1757590320","subject":"my goal: cumcumcum <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/bigcock\/\">#bigcock<\/a> <a href=\"\/tag\/trans\/\">#trans<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/femboy\/\">#femboy<\/a> [1565 tokens remaining]"},{"display_age":null,"gender":"f","location":"Washington, United States","current_show":"public","username":"mesamarie","tags":["new","18","innocent"],"is_new":false,"num_users":562,"num_followers":4428,"start_dt_utc":"2025-09-11T04:16:57.645304+00:00","country":"US","has_password":false,"private_price":60,"spy_show_price":6,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757564217,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/mesamarie.jpg?1757590320","subject":"doggyy <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/innocent\/\">#innocent<\/a> [3545 tokens remaining]"},{"display_age":18,"gender":"f","location":"In your hug","current_show":"public","username":"cielomio","tags":["anal","squirt","teen","ahegao","lovense"],"is_new":false,"num_users":695,"num_followers":197576,"start_dt_utc":"2025-09-11T04:16:56.163506+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757564216,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/cielomio.jpg?1757590320","subject":"goal: giant tsunami squirt [0 tokens remaining] hey, it&#x27;s jodi! i came after the gym and started the broadcast <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/ahegao\/\">#ahegao<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a>"},{"display_age":19,"gender":"f","location":"Lost in your thoughts \ud83e\udd84","current_show":"public","username":"entya","tags":["teen","18","young","skinny","innocent"],"is_new":false,"num_users":645,"num_followers":22628,"start_dt_utc":"2025-09-11T05:59:23.853395+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":6,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757570363,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/entya.jpg?1757590320","subject":"in the mood for fun ... are you?\ud83e\udd2d\ud83d\udc40 <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/innocent\/\">#innocent<\/a>"},{"display_age":26,"gender":"c","location":"Europe","current_show":"public","username":"kira0541","tags":["pvt","anal","dildo","squirt","lovense"],"is_new":false,"num_users":460,"num_followers":512149,"start_dt_utc":"2025-09-10T04:13:24.883120+00:00","country":"","has_password":false,"private_price":180,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757477604,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/kira0541.jpg?1757590320","subject":"goal: naked ass  and slap [302 tokens remaining] welcome to my room! <a href=\"\/tag\/pvt\/\">#pvt<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/dildo\/\">#dildo<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a>"},{"display_age":99,"gender":"f","location":"sexyland","current_show":"public","username":"misssweettie","tags":["teen","smalltits","skinny","squirt","natural"],"is_new":false,"num_users":444,"num_followers":291482,"start_dt_utc":"2025-09-11T09:45:56.793372+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757583956,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/misssweettie.jpg?1757590320","subject":"\u2b50 happy day!!! sh\u278bw! \u2b50 <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a>"},{"display_age":null,"gender":"s","location":"Australia","current_show":"public","username":"geminirises","tags":["redhead","trans","lovense","mistress","bigboobs"],"is_new":false,"num_users":337,"num_followers":54101,"start_dt_utc":"2025-09-11T10:59:23.429753+00:00","country":"AU","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588363,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/geminirises.jpg?1757590320","subject":"detention teacher shifts focus to supplementary material [860 tokens left] <a href=\"\/tag\/redhead\/\">#redhead<\/a> <a href=\"\/tag\/trans\/\">#trans<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/mistress\/\">#mistress<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a>"},{"display_age":28,"gender":"f","location":":)","current_show":"public","username":"annaise_","tags":["lovense","boobs","ass","pussytease","blonde"],"is_new":false,"num_users":506,"num_followers":151576,"start_dt_utc":"2025-09-11T10:08:34.293474+00:00","country":"","has_password":false,"private_price":240,"spy_show_price":120,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757585314,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/annaise_.jpg?1757590320","subject":"hello guys! tip fav 111\/333\/555\/777\/999\/make me smile122\/ big tip 2222 <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/boobs\/\">#boobs<\/a> <a href=\"\/tag\/ass\/\">#ass<\/a> <a href=\"\/tag\/pussytease\/\">#pussytease<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> #fit"},{"display_age":23,"gender":"f","location":"Dream Land","current_show":"public","username":"phoebepaw","tags":["skinny","young","squirt","blonde","smalltits"],"is_new":false,"num_users":440,"num_followers":141961,"start_dt_utc":"2025-09-11T09:35:58.489937+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757583358,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/phoebepaw.jpg?1757590320","subject":"welcome to my room! let&#x27;s enjoy the rest of the moments together.\u2764\ufe0f - goal: open pussy 2 min [127 tokens left] <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a>"},{"display_age":27,"gender":"f","location":"Florida, United States","current_show":"public","username":"camiliakxoxo","tags":["pussy","big","natural","latina","arab"],"is_new":false,"num_users":425,"num_followers":178677,"start_dt_utc":"2025-09-11T10:19:54.692520+00:00","country":"US","has_password":false,"private_price":240,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757585994,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/camiliakxoxo.jpg?1757590320","subject":"top off <a href=\"\/tag\/pussy\/\">#pussy<\/a> <a href=\"\/tag\/big\/\">#big<\/a> tits <a href=\"\/tag\/natural\/\">#natural<\/a> <a href=\"\/tag\/latina\/\">#latina<\/a> <a href=\"\/tag\/arab\/\">#arab<\/a> #girl #new #young [355 tokens remaining]"},{"display_age":21,"gender":"f","location":"Guess \ud83e\udd2b","current_show":"public","username":"sarilit","tags":["daddysgirl","blonde","skinny","smalltits"],"is_new":true,"num_users":629,"num_followers":7192,"start_dt_utc":"2025-09-11T02:09:45.265011+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"new","is_following":false,"source_name":"df","start_timestamp":1757556585,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sarilit.jpg?1757590320","subject":"goal: spread my pussy close up [200 tokens remaining] hey there! be polite pls,i need ur support so much!let&#x27;s get to know each other better <a href=\"\/tag\/daddysgirl\/\">#daddysgirl<\/a> <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a>"},{"display_age":null,"gender":"f","location":"Your heart","current_show":"public","username":"pretty_princess_elina","tags":["new","18","shy","natural","teen"],"is_new":false,"num_users":559,"num_followers":61394,"start_dt_utc":"2025-09-11T06:38:52.794886+00:00","country":"","has_password":false,"private_price":-1,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757572732,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/pretty_princess_elina.jpg?1757590320","subject":"drool on tits [369 tokens left] hi dear, i&#x27;m elina and welcome to my room:* <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a>"},{"display_age":null,"gender":"s","location":"Christmas Island","current_show":"public","username":"xdreamangel","tags":["bigcock","lovense","cum","anal","asian"],"is_new":false,"num_users":396,"num_followers":121278,"start_dt_utc":"2025-09-11T02:23:10.614566+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757557390,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/xdreamangel.jpg?1757590320","subject":"[0 tokens to goal] -- super cumshot and eat it!  <a href=\"\/tag\/bigcock\/\">#bigcock<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a>  <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/asian\/\">#asian<\/a> #mistress #trans #bigtits #bigass #feet"},{"display_age":99,"gender":"c","location":"Here and somewhere else at the same time.","current_show":"public","username":"realtoxxxmaria","tags":["anal","squirt","bigboobs","bigass","new"],"is_new":false,"num_users":515,"num_followers":799450,"start_dt_utc":"2025-09-11T10:46:44.375167+00:00","country":"US","has_password":false,"private_price":360,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587604,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/realtoxxxmaria.jpg?1757590320","subject":"\u2764\ufe0f my step-grandpa is strict with me. i&#x27;m horny! \u2764\ufe0f <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/new\/\">#new<\/a> [tip in ascending order from 1 to 100. next tip needed: 31]"},{"display_age":22,"gender":"c","location":"Colombia","current_show":"public","username":"april_sex_vip","tags":["smoke","ahegao","deepthroat","anal","latina"],"is_new":false,"num_users":598,"num_followers":115401,"start_dt_utc":"2025-09-11T07:47:14.945033+00:00","country":"CO","has_password":false,"private_price":60,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757576834,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/april_sex_vip.jpg?1757590320","subject":"cum face, bra off  <a href=\"\/tag\/smoke\/\">#smoke<\/a> <a href=\"\/tag\/ahegao\/\">#ahegao<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a>  <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/latina\/\">#latina<\/a>  #bdsm #creampie #braces #pvt [870 tokens remaining]"},{"display_age":26,"gender":"f","location":"planet Earth","current_show":"public","username":"snowww_white","tags":["lovense","ohmibod","interactivetoy"],"is_new":false,"num_users":305,"num_followers":378104,"start_dt_utc":"2025-09-11T10:53:59.241585+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588039,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/snowww_white.jpg?1757590320","subject":"lovense: interactive toy that vibrates with your tips <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/ohmibod\/\">#ohmibod<\/a> <a href=\"\/tag\/interactivetoy\/\">#interactivetoy<\/a>"},{"display_age":20,"gender":"f","location":"Moldova","current_show":"public","username":"kriskras__","tags":["teen","18","young","feet","skinny"],"is_new":false,"num_users":401,"num_followers":264739,"start_dt_utc":"2025-09-11T05:09:10.258629+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":240,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757567350,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/kriskras__.jpg?1757590320","subject":"<a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/feet\/\">#feet<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> all goals completed!!!"},{"display_age":27,"gender":"c","location":"dreamland","current_show":"public","username":"anabel054","tags":["pvt","naked","lovense","dildo","squirt"],"is_new":false,"num_users":457,"num_followers":1285109,"start_dt_utc":"2025-09-11T06:15:15.529882+00:00","country":"","has_password":false,"private_price":180,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757571315,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/anabel054.jpg?1757590320","subject":"goal: doggy and slapp as madison [303 tokens remaining] ) <a href=\"\/tag\/pvt\/\">#pvt<\/a> <a href=\"\/tag\/naked\/\">#naked<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/dildo\/\">#dildo<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a>"},{"display_age":21,"gender":"m","location":"EDGING PARTY","current_show":"public","username":"tommyjoyer","tags":["lovense","cum","anal","cute","uncut"],"is_new":false,"num_users":379,"num_followers":121879,"start_dt_utc":"2025-09-11T08:21:28.158991+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757578888,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/tommyjoyer.jpg?1757590320","subject":"goal reached!  thanks to all tippers!  <a href=\"\/tag\/lovense\/\">#lovense<\/a>  <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a>  <a href=\"\/tag\/cute\/\">#cute<\/a> <a href=\"\/tag\/uncut\/\">#uncut<\/a>"},{"display_age":18,"gender":"f","location":"Poland","current_show":"public","username":"myriambirkett","tags":["18","new","shy","lovense","bigboobs"],"is_new":true,"num_users":451,"num_followers":8133,"start_dt_utc":"2025-09-11T05:17:51.313447+00:00","country":"","has_password":false,"private_price":6,"spy_show_price":6,"is_gaming":false,"is_age_verified":true,"label":"new","is_following":false,"source_name":"df","start_timestamp":1757567871,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/myriambirkett.jpg?1757590320","subject":"third day with lush! goal: two fingers in my wet pussy.!^^ hello my name is greta <a href=\"\/tag\/18\/\">#18<\/a> yo from poland and im <a href=\"\/tag\/new\/\">#new<\/a> here <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> [126 tokens remaining]"},{"display_age":null,"gender":"f","location":"\ud83d\udc9cAlways on your mind\ud83d\udc9c","current_show":"public","username":"alexxiskye","tags":["brunette","bigass","bigboobs","teen","daddy"],"is_new":false,"num_users":445,"num_followers":218370,"start_dt_utc":"2025-09-11T05:37:45.003673+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757569065,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/alexxiskye.jpg?1757590320","subject":"goal reached!  thanks to all tippers! fav vibes 100 120 160 200 333 400  <a href=\"\/tag\/brunette\/\">#brunette<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/daddy\/\">#daddy<\/a>"},{"display_age":null,"gender":"f","location":"Ask me in pvt","current_show":"public","username":"miss_diamond__","tags":["brunette","bigboobs","bigass","cumshow","anal"],"is_new":false,"num_users":395,"num_followers":786447,"start_dt_utc":"2025-09-11T07:06:34.784474+00:00","country":"","has_password":false,"private_price":240,"spy_show_price":150,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757574394,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/miss_diamond__.jpg?1757590320","subject":"hiii&lt;3 happy week&lt;3 <a href=\"\/tag\/brunette\/\">#brunette<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/cumshow\/\">#cumshow<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a>"},{"display_age":null,"gender":"f","location":"1307","current_show":"public","username":"butteflai","tags":["18","teen","bigboobs","young","natural"],"is_new":false,"num_users":400,"num_followers":45272,"start_dt_utc":"2025-09-11T06:18:14.857201+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757571494,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/butteflai.jpg?1757590320","subject":"take off panties <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a> [420 tokens remaining]"},{"display_age":null,"gender":"m","location":"Chaturbate","current_show":"public","username":"mattiestreams69","tags":["pvt","cum","young","18","muscle"],"is_new":false,"num_users":317,"num_followers":22753,"start_dt_utc":"2025-09-11T10:32:53.017176+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":54,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757586773,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/mattiestreams69.jpg?1757590320","subject":"let&#x27;s explore desire together!\ud83d\ude80\ud83d\udcab current goal: cocks out  !?  <a href=\"\/tag\/pvt\/\">#pvt<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/muscle\/\">#muscle<\/a>"},{"display_age":24,"gender":"c","location":"South Holland, The Netherlands","current_show":"public","username":"felice_favn","tags":["tits","facial","lovense","bigboobs","deepthroat"],"is_new":false,"num_users":634,"num_followers":63729,"start_dt_utc":"2025-09-11T10:15:53.931031+00:00","country":"","has_password":false,"private_price":30,"spy_show_price":12,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757585753,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/felice_favn.jpg?1757590320","subject":"goal: pov titsjob <a href=\"\/tag\/tits\/\">#tits<\/a> <a href=\"\/tag\/facial\/\">#facial<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a>  <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a>"},{"display_age":20,"gender":"f","location":"Your room","current_show":"public","username":"sweet_69billy","tags":["18","squirt","boobs","pvt","flexible"],"is_new":false,"num_users":364,"num_followers":429726,"start_dt_utc":"2025-09-11T02:00:09.331870+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757556009,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sweet_69billy.jpg?1757590320","subject":"ride dildo [330 tokens left] <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/boobs\/\">#boobs<\/a> <a href=\"\/tag\/pvt\/\">#pvt<\/a> <a href=\"\/tag\/flexible\/\">#flexible<\/a> #asmr"},{"display_age":18,"gender":"f","location":"A country of tulips","current_show":"public","username":"fredericabledsoe","tags":["new","skinny","18","smalltits","shy"],"is_new":false,"num_users":494,"num_followers":48780,"start_dt_utc":"2025-09-11T04:24:52.791638+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757564692,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/fredericabledsoe.jpg?1757590320","subject":"my name is amy and i am  <a href=\"\/tag\/new\/\">#new<\/a> and <a href=\"\/tag\/skinny\/\">#skinny<\/a> model on cb <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a>  goal:  make my ass red [197 tokens remaining]"},{"display_age":21,"gender":"f","location":"Asia","current_show":"public","username":"amyalwayshere","tags":["asian","young","lush","teen","feet"],"is_new":false,"num_users":206,"num_followers":161954,"start_dt_utc":"2025-09-11T05:25:54.513181+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757568354,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/amyalwayshere.jpg?1757590320","subject":"collecting money for cartier watch ^^ goal is wine \ud83c\udf7e\ud83e\udd42\ud83c\udf7e\ud83e\udd42 with 107 remaining to goal! <a href=\"\/tag\/asian\/\">#asian<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/lush\/\">#lush<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/feet\/\">#feet<\/a>"},{"display_age":null,"gender":"c","location":"Norte de Santander Department, Colombia","current_show":"public","username":"virgo_caos77","tags":[],"is_new":false,"num_users":517,"num_followers":22387,"start_dt_utc":"2025-09-11T08:04:29.122479+00:00","country":"CO","has_password":false,"private_price":60,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757577869,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/virgo_caos77.jpg?1757590320","subject":"ticket show 200tk for fuck ass girl \ud83e\udd24 [730 tokens remaining]"},{"display_age":null,"gender":"c","location":"Spain","current_show":"public","username":"maca_hugo","tags":["latina","bigass","bigboobs"],"is_new":false,"num_users":449,"num_followers":153470,"start_dt_utc":"2025-09-11T09:54:10.769129+00:00","country":"ES","has_password":false,"private_price":120,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757584450,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/maca_hugo.jpg?1757590320","subject":"[143 tokens to goal] -- current goal: sloppy blowjob to the dildo while hugo destroy my pussy in missionary  \ud83d\ude08 at 600 tokens -- 5 very hot goals + cum ticket show at the end <a href=\"\/tag\/latina\/\">#latina<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a>"},{"display_age":20,"gender":"f","location":"Poland, Gda\u0144sk","current_show":"public","username":"_annybunny_","tags":["blonde","18","teen","natural","bigboobs"],"is_new":false,"num_users":409,"num_followers":300780,"start_dt_utc":"2025-09-11T07:01:40.275354+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":54,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757574100,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/_annybunny_.jpg?1757590320","subject":"goal: hands up it`s police [316 tokens remaining] i&#x27;m nabif\ud83d\ude0bi&#x27;m back he he\ud83e\udd73 <a href=\"\/tag\/blonde\/\">#blonde<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a>"},{"display_age":18,"gender":"f","location":"Czech Republic, Prague","current_show":"public","username":"tashinadoncaster","tags":["new","shy","teen","skinny","asian"],"is_new":false,"num_users":405,"num_followers":19984,"start_dt_utc":"2025-09-11T07:41:08.532333+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757576468,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/tashinadoncaster.jpg?1757590320","subject":"umm, hi! i`m viola:) \ud83d\udc79goal :touch my boobs and make nipples hard under top \ud83d\udc79  <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/asian\/\">#asian<\/a> [8 tokens remaining]"},{"display_age":25,"gender":"f","location":"Wonderland\u2728","current_show":"public","username":"alice_pinkys","tags":["bigboobs","bbc","ahegao","deepthroat","saliva"],"is_new":false,"num_users":388,"num_followers":221995,"start_dt_utc":"2025-09-11T08:46:10.926587+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":180,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757580370,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/alice_pinkys.jpg?1757590320","subject":"\u2660deepthroat queen \u2660 \/\/ goal: \ud83d\udca6lick ur cock with  whipped cream\ud83d\udca6 [93 tokens left] \/\/ epic goal: \ud83d\udca6reverse cowgirl on huge bbc\ud83d\udca6 [27796 tokens left] <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bbc\/\">#bbc<\/a> <a href=\"\/tag\/ahegao\/\">#ahegao<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a> <a href=\"\/tag\/saliva\/\">#saliva<\/a>"},{"display_age":22,"gender":"c","location":"Europe","current_show":"public","username":"ollistiw","tags":["couple","teen","deepthroat","cum"],"is_new":false,"num_users":694,"num_followers":78937,"start_dt_utc":"2025-09-11T07:52:28.550975+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757577148,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/ollistiw.jpg?1757590320","subject":"current goal: suck nipples at 220 tokens -- next goal: play asshole -- hi gents! olli has a toy, try tip\ud83e\uddf822\ud83e\uddf844\ud83e\uddf866\ud83e\uddf888, it makes her scream and receive pleasure;) <a href=\"\/tag\/couple\/\">#couple<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a>"},{"display_age":22,"gender":"f","location":"CB","current_show":"public","username":"quintessencel","tags":["bigtits","bigass","squirt","teen","natural"],"is_new":false,"num_users":403,"num_followers":296085,"start_dt_utc":"2025-09-11T08:33:16.957522+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757579596,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/quintessencel.jpg?1757590320","subject":"squirt?\u2665 35\/55\/111\/222\/333\/555 <a href=\"\/tag\/bigtits\/\">#bigtits<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a>"},{"display_age":36,"gender":"f","location":"USA","current_show":"public","username":"yourkat","tags":["milf","bigboobs","squirt","mommy"],"is_new":false,"num_users":514,"num_followers":713288,"start_dt_utc":"2025-09-11T09:36:15.837120+00:00","country":"","has_password":false,"private_price":150,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757583375,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/yourkat.jpg?1757590320","subject":"let&#x27;s  have fun ! make me squirt hard! - goal: ride dildo and squirt <a href=\"\/tag\/milf\/\">#milf<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/mommy\/\">#mommy<\/a>"},{"display_age":null,"gender":"c","location":"in your dreams <3","current_show":"public","username":"kontikss","tags":["lovense","facefuck","teen","cumface","squirt"],"is_new":false,"num_users":562,"num_followers":123842,"start_dt_utc":"2025-09-11T11:00:15.069255+00:00","country":"","has_password":false,"private_price":72,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588415,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/kontikss.jpg?1757590320","subject":"ticket show sales [20 tokens]: cumshow (write \/poll to vote where cum) \ud83d\udca6\ud83d\udca6 votes: 26tk - facial, 19tk - mouth, 22tk - creampie, 31tk - throarpie <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/facefuck\/\">#facefuck<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/cumface\/\">#cumface<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a>"},{"display_age":29,"gender":"f","location":"In the World of dream","current_show":"public","username":"1dream_magical","tags":["cum","squirt","lovense","ohmibod","interactivetoy"],"is_new":false,"num_users":288,"num_followers":297818,"start_dt_utc":"2025-09-11T08:08:01.792168+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":0,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757578081,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/1dream_magical.jpg?1757590320","subject":"\ud83d\udc95\ud83d\ude0d make me happy, take me to orgasm \ud83d\ude0d\ud83d\udc95\u2757\u2757 - multi-goal :  <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/ohmibod\/\">#ohmibod<\/a> <a href=\"\/tag\/interactivetoy\/\">#interactivetoy<\/a>"},{"display_age":99,"gender":"f","location":"Here","current_show":"public","username":"ellie_land","tags":["bigboobs","petite","tattoo","skinny","teen"],"is_new":false,"num_users":402,"num_followers":217933,"start_dt_utc":"2025-09-11T09:03:18.345123+00:00","country":"","has_password":false,"private_price":72,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757581398,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/ellie_land.jpg?1757590320","subject":"goal: love u! \ud83d\udc96 hello, gentlemen! i will be glad to have fun with you and give you pleasure! \ud83d\udc96 <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/petite\/\">#petite<\/a> <a href=\"\/tag\/tattoo\/\">#tattoo<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a>"},{"display_age":99,"gender":"f","location":"Everywhere","current_show":"public","username":"amj_b","tags":["bigboobs","bigass","daddy"],"is_new":false,"num_users":468,"num_followers":359551,"start_dt_utc":"2025-09-11T09:45:02.809980+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":90,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757583902,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/amj_b.jpg?1757590320","subject":"hello, top off...make me cum daddy.best vibe 111,222,333,444. naked cum show with dildo in pvt  <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/daddy\/\">#daddy<\/a>"},{"display_age":19,"gender":"f","location":"Dreams","current_show":"public","username":"fideliastagnitto","tags":["18","skinny","smalltits","lovense","shy"],"is_new":false,"num_users":413,"num_followers":56792,"start_dt_utc":"2025-09-11T03:05:20.520619+00:00","country":"","has_password":false,"private_price":72,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757559920,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/fideliastagnitto.jpg?1757590320","subject":"hello guys, i&#x27;m isabela&lt;3 goal: masturbate my pussy until i cum <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/shy\/\">#shy<\/a> [373 tokens remaining]"},{"display_age":20,"gender":"f","location":"Uusimaa, Finland","current_show":"public","username":"milly_shy","tags":["feet","teen","blowjob","smalltits"],"is_new":false,"num_users":396,"num_followers":342702,"start_dt_utc":"2025-09-11T06:38:35.544262+00:00","country":"","has_password":false,"private_price":6,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757572715,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/milly_shy.jpg?1757590320","subject":"fuck that puff wet pussy with 2 fingers (moisten me good before dildo enters inside me) \u2764\ufe0f <a href=\"\/tag\/feet\/\">#feet<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/blowjob\/\">#blowjob<\/a> <a href=\"\/tag\/smalltits\/\">#smalltits<\/a> [335 tokens remaining]"},{"display_age":null,"gender":"c","location":"Stockholm","current_show":"public","username":"petal_couple","tags":["new","deepthroat","couple","sex","anal"],"is_new":false,"num_users":494,"num_followers":42557,"start_dt_utc":"2025-09-11T08:40:42.487210+00:00","country":"","has_password":false,"private_price":72,"spy_show_price":42,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757580042,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/petal_couple.jpg?1757590320","subject":"make a one minute blowjob [150 tokens left] <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/deepthroat\/\">#deepthroat<\/a> <a href=\"\/tag\/couple\/\">#couple<\/a> <a href=\"\/tag\/sex\/\">#sex<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a>"},{"display_age":18,"gender":"f","location":"Dream city","current_show":"public","username":"dark_ester","tags":["18","new","squirt","ahegao","asian"],"is_new":false,"num_users":272,"num_followers":44389,"start_dt_utc":"2025-09-11T10:38:17.966774+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757587097,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/dark_ester.jpg?1757590320","subject":"\u2764\ufe0fdoggy\u2764\ufe0f <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/new\/\">#new<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a>  <a href=\"\/tag\/ahegao\/\">#ahegao<\/a> <a href=\"\/tag\/asian\/\">#asian<\/a> [63 tokens remaining]"},{"display_age":null,"gender":"s","location":"Europe","current_show":"public","username":"sexy_vania","tags":["lovense","bigcock","cum","trans","anal"],"is_new":false,"num_users":404,"num_followers":158194,"start_dt_utc":"2025-09-11T11:09:00.451888+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":30,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588940,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/sexy_vania.jpg?1757590320","subject":"welcome to my room! - goal: closeup suck vania&#x27;s cock deepthroat  [166 tokens left] <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/bigcock\/\">#bigcock<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a> <a href=\"\/tag\/trans\/\">#trans<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> #lesbian #18 #bigboobs <a href=\"\/tag\/cum\/\">#cum<\/a> #deepthroat #feet #young #milf #couple #blonde #blow"},{"display_age":20,"gender":"s","location":"\ud835\udcd3\ud835\udcfb\ud835\udcee\ud835\udcea\ud835\udcf6\ud835\udcf5\ud835\udcea\ud835\udcf7\ud835\udced","current_show":"public","username":"alicerosee___","tags":["latina","natural","pvt","trans","cum"],"is_new":false,"num_users":330,"num_followers":24574,"start_dt_utc":"2025-09-11T06:19:30.213071+00:00","country":"","has_password":false,"private_price":72,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757571570,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/alicerosee___.jpg?1757590320","subject":"monday with me!!!  :p - goal: explode your celestial milk for me alice\ud83d\udca6 [3726 tokens left] <a href=\"\/tag\/latina\/\">#latina<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a> <a href=\"\/tag\/pvt\/\">#pvt<\/a> <a href=\"\/tag\/trans\/\">#trans<\/a> <a href=\"\/tag\/cum\/\">#cum<\/a>"},{"display_age":46,"gender":"f","location":"Ro","current_show":"public","username":"mis_eva","tags":["ohmibod","natural","bigboobs","milf","pvt"],"is_new":false,"num_users":337,"num_followers":783751,"start_dt_utc":"2025-09-11T10:54:45.399034+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588085,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/mis_eva.jpg?1757590320","subject":"*privates on** make me hot, make me wet, make me moan, make me cum~~ - multi-goal :  wet t-shirt show ! high vibes makes me cum ! \u2764\ufe0f <a href=\"\/tag\/ohmibod\/\">#ohmibod<\/a> <a href=\"\/tag\/natural\/\">#natural<\/a> <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/milf\/\">#milf<\/a> <a href=\"\/tag\/pvt\/\">#pvt<\/a> #cum #feet #c2c #bigtits #hot #blonde #"},{"display_age":18,"gender":"c","location":"Netherlands","current_show":"public","username":"ellatwox","tags":["sex","pvt","young","domi","18"],"is_new":false,"num_users":555,"num_followers":3736,"start_dt_utc":"2025-09-11T10:04:56.985022+00:00","country":"","has_password":false,"private_price":60,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757585096,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/ellatwox.jpg?1757590320","subject":"cream pie !!!!. lets enjoy! <a href=\"\/tag\/sex\/\">#sex<\/a> <a href=\"\/tag\/pvt\/\">#pvt<\/a> <a href=\"\/tag\/young\/\">#young<\/a> <a href=\"\/tag\/domi\/\">#domi<\/a> <a href=\"\/tag\/18\/\">#18<\/a> [760 tokens remaining]"},{"display_age":null,"gender":"f","location":"\ud835\ude4b\ud835\ude61\ud835\ude56\ud835\ude63\ud835\ude5a\ud835\ude69 \ud835\ude40\ud835\ude56\ud835\ude67\ud835\ude69\ud835\ude5d","current_show":"public","username":"melissabarbie","tags":["bigboobs","bigtits","lovense","squirt","oil"],"is_new":false,"num_users":346,"num_followers":191909,"start_dt_utc":"2025-09-11T08:36:34.264819+00:00","country":"","has_password":false,"private_price":90,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757579794,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/melissabarbie.jpg?1757590320","subject":"\u2b50help me squirt guys\u2b50my favorite vibration: 77\/111\/333  <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/bigtits\/\">#bigtits<\/a> <a href=\"\/tag\/lovense\/\">#lovense<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/oil\/\">#oil<\/a> #"},{"display_age":18,"gender":"f","location":"Paradise","current_show":"public","username":"felissiany","tags":["bigboobs","18","squirt","teen","skinny"],"is_new":false,"num_users":381,"num_followers":401472,"start_dt_utc":"2025-09-11T09:12:45.573226+00:00","country":"","has_password":false,"private_price":120,"spy_show_price":66,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757581965,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/felissiany.jpg?1757590320","subject":"goal: lick my tits [337 tokens remaining] i&#x27;m nova <a href=\"\/tag\/bigboobs\/\">#bigboobs<\/a> <a href=\"\/tag\/18\/\">#18<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a> <a href=\"\/tag\/teen\/\">#teen<\/a> <a href=\"\/tag\/skinny\/\">#skinny<\/a>"},{"display_age":99,"gender":"f","location":"chaturbate","current_show":"public","username":"kinky_malina","tags":["bigass","anal","hairy","hairyarmpits","squirt"],"is_new":false,"num_users":343,"num_followers":91505,"start_dt_utc":"2025-09-11T09:23:02.406774+00:00","country":"","has_password":false,"private_price":42,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757582582,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/kinky_malina.jpg?1757590320","subject":"heeey! good spread for good lick! \u2661 \/tipmenu or in bio \u2661 pvt on) <a href=\"\/tag\/bigass\/\">#bigass<\/a> <a href=\"\/tag\/anal\/\">#anal<\/a> <a href=\"\/tag\/hairy\/\">#hairy<\/a> <a href=\"\/tag\/hairyarmpits\/\">#hairyarmpits<\/a> <a href=\"\/tag\/squirt\/\">#squirt<\/a>"},{"display_age":18,"gender":"s","location":"USA","current_show":"public","username":"arina_rose","tags":["femboy","punk","trans","couple"],"is_new":false,"num_users":250,"num_followers":47724,"start_dt_utc":"2025-09-11T10:56:17.188007+00:00","country":"","has_password":false,"private_price":180,"spy_show_price":18,"is_gaming":false,"is_age_verified":true,"label":"public","is_following":false,"source_name":"df","start_timestamp":1757588177,"img":"https:\/\/thumb.live.mmcdn.com\/riw\/arina_rose.jpg?1757590320","subject":"\ud83c\udf08 stream with trans and emo-punk \ud83d\udc9c\ud83d\udc80 -  <a href=\"\/tag\/femboy\/\">#femboy<\/a> , <a href=\"\/tag\/punk\/\">#punk<\/a> , <a href=\"\/tag\/trans\/\">#trans<\/a> , <a href=\"\/tag\/couple\/\">#couple<\/a>"}],"total_count":6113,"all_rooms_count":6857,"room_list_id":"28075437-621a-4241-924b-69cde9048c8f","bls_payload":"{\"vertex_attr_token\": \"\"}","has_fingerprint":true}'''
            response.raise_for_status()
            data = response.json()
            rooms = data.get("rooms", [])
            
            # Cache for 1 minute
            save_data(ROOM_CACHE_FILE, {
                'rooms': rooms,
                'expires': time.time() + 60
            })
        
        rooms.sort(key=lambda r: r.get("num_users", 0), reverse=True)
        
        # Enhance room data
        current_time = datetime.now().timestamp()
        for room in rooms:
            room['flag'] = country_to_flag(room.get('country', ''))
            room['gender_display'] = gender_to_display(room.get('gender', ''))
            room['uptime'] = int(current_time - room.get('start_time', current_time))
            room['is_new'] = room['uptime'] < 900  # Less than 15 minutes
            
        # Calculate stats
        total_viewers = sum(r.get("num_users", 0) for r in rooms)
        private_rooms = sum(1 for r in rooms if r.get("private_price", 0) > 0)
        
        # Get unique tags
        all_tags = sorted({tag.lower() for r in rooms for tag in r.get("tags", [])})
        
        # Load preferences
        preferences = load_data(PREFERENCES_FILE, {
            'dark_mode': False,
            'quick_filter': '',
            'favorites_filter': 'all',
            'sort_method': 'viewers-desc',
            'viewer_min': 0,
            'viewer_max': 10000,
            'show_type': 'all'
        })
        
    except Exception as e:
        print(f"Error fetching room list: {str(e)}")
        rooms = []
        all_tags = []
        total_viewers = 0
        private_rooms = 0
        preferences = {}

    return render_template_string(
        HTML_TEMPLATE, 
        rooms=rooms, 
        all_tags=all_tags,
        total_viewers=total_viewers,
        private_rooms=private_rooms,
        preferences=preferences,
        format_duration=format_duration,
        timestamp=int(time.time() * 1000)  # Timestamp for cache busting
    )

@app.route("/room/<username>/summary")
def summary(username):
    try:
        # Get the detailed room information
        api_url = f"https://chaturbate.com/api/chatvideocontext/{username}/"
        response = requests.get(api_url, headers=API_HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Parse apps running (if available)
        apps_running = []
        if data.get("apps_running"):
            try:
                apps_running = eval(data["apps_running"])
            except:
                apps_running = []
        
        # Extract satisfaction score
        satisfaction_score = data.get("satisfaction_score", {})
        
        # Extract the most relevant summary information
        summary_data = {
            "room_title": data.get("room_title", "No title"),
            "num_viewers": data.get("num_viewers", 0),
            "broadcaster_gender": data.get("broadcaster_gender", ""),
            "private_show_price": data.get("private_show_price", 0),
            "allow_private_shows": data.get("allow_private_shows", False),
            "allow_show_recordings": data.get("allow_show_recordings", False),
            "summary_card_image": data.get("summary_card_image", ""),
            "apps_running": apps_running,
            "chat_rules": data.get("chat_rules", ""),
            "quality": data.get("quality", {}).get("quality", "unknown"),
            "hls_source": data.get("hls_source", ""),
            "is_age_verified": data.get("is_age_verified", False),
            "satisfaction_score": {
                "percent": satisfaction_score.get("percent", 0),
                "up_votes": satisfaction_score.get("up_votes", 0),
                "down_votes": satisfaction_score.get("down_votes", 0),
                "max": satisfaction_score.get("max", 0)
            },
            "social_links": [
                {"platform": "Twitter", "url": "https://twitter.com/example"},
                {"platform": "Instagram", "url": "https://instagram.com/example"}
            ]
        }
        
        return jsonify(summary_data)
        
    except Exception as e:
        print(f"Error fetching summary for {username}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/room/<username>/users")
def room_users(username):
    try:
        # Fetch user list from Chaturbate API
        api_url = f"https://chaturbate.com/api/getchatuserlist/?roomname={username}&private=false&sort_by=a&exclude_staff=false"
        response = requests.get(api_url, headers=API_HEADERS, timeout=5)
        response.raise_for_status()
        
        # Parse the response
        raw_data = response.text
        users = []
        
        # The format is: count,username|status|gender|?,username2|status|gender|?,...
        if raw_data:
            parts = raw_data.split(',')
            if len(parts) > 1:
                for user_info in parts[1:]:
                    user_parts = user_info.split('|')
                    if len(user_parts) >= 3:
                        username = user_parts[0]
                        status = user_parts[1]
                        gender = user_parts[2]
                        
                        # Map gender codes to full words
                        gender_map = {
                            'm': 'Male',
                            'f': 'Female',
                            't': 'Trans',
                            'c': 'Couple'
                        }
                        
                        users.append({
                            "username": username,
                            "status": status,
                            "gender": gender_map.get(gender, gender)
                        })
        
        return jsonify({
            "users": users,
            "count": len(users)
        })
        
    except Exception as e:
        print(f"Error fetching user list for {username}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_favorites')
def get_favorites():
    return jsonify({'favorites': load_data(FAVORITES_FILE, [])})

@app.route('/save_favorites', methods=['POST'])
def save_favorites():
    data = request.get_json()
    save_data(FAVORITES_FILE, data.get('favorites', []))
    return jsonify({'status': 'success'})

@app.route('/get_notes')
def get_notes():
    return jsonify(load_data(NOTES_FILE, {}))

@app.route('/save_notes', methods=['POST'])
def save_notes():
    data = request.get_json()
    save_data(NOTES_FILE, data)
    return jsonify({'status': 'success'})

@app.route('/get_preferences')
def get_preferences():
    return jsonify(load_data(PREFERENCES_FILE, {
        'dark_mode': False,
        'quick_filter': '',
        'favorites_filter': 'all',
        'sort_method': 'viewers-desc',
        'viewer_min': 0,
        'viewer_max': 10000,
        'show_type': 'all',
        'active_tags': []
    }))

@app.route('/save_preferences', methods=['POST'])
def save_preferences():
    data = request.get_json()
    save_data(PREFERENCES_FILE, data)
    return jsonify({'status': 'success'})

@app.route('/api/refresh')
def refresh_data():
    try:
        response = requests.get(
            "https://chaturbate.com/api/ts/roomlist/room-list?limit=100", 
            headers=API_HEADERS,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        rooms = data.get("rooms", [])
        
        # Check which favorites are online
        favorites = load_data(FAVORITES_FILE, [])
        online_favorites = [
            room['username'] for room in rooms 
            if room['username'] in favorites
        ]
        
        # Update cache
        save_data(ROOM_CACHE_FILE, {
            'rooms': rooms,
            'expires': time.time() + 60
        })
        
        return jsonify({
            'rooms': rooms,
            'online_favorites': online_favorites
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Clip management routes
@app.route('/save_clip', methods=['POST'])
def save_clip():
    try:
        data = request.get_json()
        username = data.get('username')
        clip_data = data.get('clipData')
        
        # Load existing clips
        clips = load_data(CLIPS_FILE, {})
        
        if username not in clips:
            clips[username] = []
        
        # Add new clip
        clip_id = str(int(time.time() * 1000))
        clips[username].append({
            'id': clip_id,
            'timestamp': datetime.now().isoformat(),
            'data': clip_data
        })
        
        # Save updated clips
        save_data(CLIPS_FILE, clips)
        
        return jsonify({'success': True, 'id': clip_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_clips/<username>')
def get_clips(username):
    try:
        clips = load_data(CLIPS_FILE, {})
        return jsonify(clips.get(username, []))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_clip/<clip_id>', methods=['DELETE'])
def delete_clip(clip_id):
    try:
        clips = load_data(CLIPS_FILE, {})
        
        # Find and remove the clip
        for username, user_clips in clips.items():
            clips[username] = [clip for clip in user_clips if clip['id'] != clip_id]
        
        # Save updated clips
        save_data(CLIPS_FILE, clips)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    # Initialize data files if they don't exist
    if not os.path.exists(FAVORITES_FILE):
        save_data(FAVORITES_FILE, [])
    if not os.path.exists(NOTES_FILE):
        save_data(NOTES_FILE, {})
    if not os.path.exists(PREFERENCES_FILE):
        save_data(PREFERENCES_FILE, {})
    if not os.path.exists(ROOM_CACHE_FILE):
        save_data(ROOM_CACHE_FILE, {})
    if not os.path.exists(CLIPS_FILE):
        save_data(CLIPS_FILE, {})
        

    app.run(debug=True, port=5000)
