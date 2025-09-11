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
            response = requests.get(
                "https://chaturbate.com/api/ts/roomlist/room-list?limit=100", 
                headers=API_HEADERS,
                timeout=10
            )
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