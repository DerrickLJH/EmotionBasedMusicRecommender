from dotenv import load_dotenv
import requests
import base64
import os
import threading
import time

from flask import Flask, render_template, Response, jsonify, request, copy_current_request_context, redirect, url_for
import pandas as pd
from backend import get_track_by_mood
import cv2
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.layers import *

app = Flask(__name__, template_folder='templates', static_folder='static')

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

conn_params = {
    'user': 'root',
    'password': 'password',
    'host': 'localhost',
    'database': 'dataengproj'
}

SPOTIFY_URL = "https://api.spotify.com/v1/"

"""Defining the different emotions"""
Emotion_Classes = ['Angry',
                   'Disgust',
                   'Fear',
                   'Happy',
                   'Neutral',
                   'Sad',
                   'Surprise']

url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
filename = "haarcascade_frontalface_default.xml"

response = requests.get(url)
with open(filename, "wb") as file:
    file.write(response.content)

print("File downloaded successfully.")

faceCascade = cv2.CascadeClassifier(filename)

"""Loading of model"""
ResNet50V2_Model = tf.keras.models.load_model("ResNet50v2.E5")

global_progress = 0

cap = cv2.VideoCapture(0)
recording = False
out = None
final_mood = None
still_processing = False
total_files = 0

def clear_frames_folder(folder_path):
    # Get a list of all the files in the folder
    files = os.listdir(folder_path)

    # Loop through each file and delete it
    for file in files:
        file_path = os.path.join(folder_path, file)
        os.remove(file_path)

    print("Folder 'frames' cleared.")


def get_access_token():
    auth_string = CLIENT_ID + ":" + CLIENT_SECRET
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = 'https://accounts.spotify.com/api/token'
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {'grant_type': 'client_credentials'}
    result = requests.post(url, headers=headers, data=data)
    json_result = result.json()
    token = json_result["access_token"]
    return token


def get_track_info(track_id):
    url = f'{SPOTIFY_URL}tracks/{track_id}'
    headers = {'Authorization': 'Bearer ' + get_access_token()}
    response = requests.get(url, headers=headers)
    track_data = response.json()
    return track_data


def get_artist_genre(artist_name):
    url = f'{SPOTIFY_URL}search'
    headers = {'Authorization': 'Bearer ' + get_access_token()}
    params = {
        'q': artist_name,
        'type': 'artist',
        'limit': 1
    }
    response = requests.get(url, headers=headers, params=params)
    artist_data = response.json()
    if artist_data["artists"]["items"]:
        genres = artist_data["artists"]["items"][0]["genres"]
        if genres:
            return genres
    return ['N/A']


def get_album_cover(artist_name):
    url = f'{SPOTIFY_URL}search'
    headers = {'Authorization': 'Bearer ' + get_access_token()}
    params = {
        'q': artist_name,
        'type': 'album',
        'limit': 1
    }
    response = requests.get(url, headers=headers, params=params)
    search_data = response.json()
    if search_data["albums"]["items"]:
        album = search_data["albums"]["items"][0]
        album_info = {
            'name': album["name"],
            'image_url': get_album_image(album["id"])
        }
        return album_info
    return None


def get_album_image(album_id):
    url = f'{SPOTIFY_URL}albums/{album_id}'
    headers = {'Authorization': 'Bearer ' + get_access_token()}
    response = requests.get(url, headers=headers)
    album_data = response.json()
    if "images" in album_data and len(album_data["images"]) > 0:
        return album_data["images"][0]["url"]
    return None


@app.route('/')
def homepage():
    return render_template('homepage.html')


@app.route('/permission_screen')
def permission_screen():
    return render_template('camera_permission.html')


def generate_frames():
    global out, recording
    while True:
        success, img = cap.read()
        if success:
            try:
                ret, buffer = cv2.imencode('.jpg', cv2.flip(img, 1))
                img = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')
            except Exception as e:
                pass
        else:
            pass


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/recording_screen')
def recording_screen():
    return render_template('recording_screen.html')


def start_recording():
    global recording
    recording = True
    frame_count = 0
    os.makedirs("frames", exist_ok=True)  # Create the "frames" folder if it doesn't exist

    while recording:
        success, img = cap.read()
        if success:
            # Save the frame as a JPG image in the "frames" folder
            frame_file = os.path.join("frames", f"frame_{frame_count:04d}.jpg")
            cv2.imwrite(frame_file, img)

            frame_count += 1


@app.route('/start_recording', methods=['POST'])
def start_recording_route():
    global final_mood
    final_mood = None
    start_recording()
    return "", 200


@app.route('/stop_recording', methods=['POST'])
def stop_recording_route():
    global recording, still_processing
    if recording:
        recording = False  # Set recording flag to stop the current recording

    @copy_current_request_context
    def process_frames():
        global final_mood, still_processing
        final_mood = run_model(update_progress)
        still_processing = False
        clear_frames_folder(folder_path='frames')
        return ""

    while still_processing:
        time.sleep(0.1)  # Wait for processing to complete
    processing_thread = threading.Thread(target=process_frames)
    processing_thread.start()
    still_processing = True
    return "", 200


@app.route('/loading_screen')
def loading_screen():
    return render_template('loading_screen.html')


@app.route('/song_type_choice')
def song_type_choice():
    global final_mood
    mood_from_model = final_mood
    return render_template('song_type_choice.html', mood_from_model=mood_from_model)


@app.route('/songs_reco', methods=['POST'])
def index():
    selected_mood = request.form.get('selected_mood')
    if selected_mood == 'Disgust':
        mood_from_model = 'Disgust'
        selected_playlist = 'Sad'

    else:
        global final_mood
        mood_from_model = final_mood
        selected_playlist = selected_mood

    tracks = get_track_by_mood(selected_playlist, conn_params)
    df = pd.DataFrame(tracks)
    if not df.empty:
        track_ids = df.iloc[:, 3].tolist()
        track_info_list = []

        for track_id in track_ids:
            track_data = get_track_info(track_id)
            artist_name = track_data['artists'][0]['name']
            genre = get_artist_genre([name for name in artist_name])
            album_image = get_album_cover(artist_name)  # Add this line to get the album image URL

            track_info = {
                'track_name': track_data['name'],
                'artist': artist_name,
                'album': track_data['album']['name'],
                'preview_url': track_data['preview_url'],
                'genre': genre[0] if genre else 'N/A',
                'image_url': album_image['image_url'] if album_image else 'N/A'
                # Include the album image URL in the track_info dictionary
            }
            track_info_list.append(track_info)

        return render_template('songs_reco.html', track_info_list=track_info_list, mood_from_model=mood_from_model,
                               selected_playlist=selected_playlist)

    return render_template('songs_reco.html', track_info=None)


@app.route('/model_processing_progress')
def model_processing_progress():
    # Return the stored progress value as JSON
    global global_progress
    return jsonify(global_progress)


def update_progress(progress):
    # Store the progress value in a global variable
    global global_progress
    global_progress = progress


def run_model(progress_callback):
    global global_progress
    global_progress = 0
    folder_path = "frames"
    final_emotion, emotions_images = process_folder(folder_path, Emotion_Classes, progress_callback)
    return final_emotion


"""Process images from the folder "frame" and run model on each image"""


def process_folder(folder_path, class_names, progress_callback):
    global total_files
    emotions_count = {}
    emotions_images = {}

    total_files = len([file for file in os.listdir(folder_path) if file.lower().endswith((".jpg", ".jpeg", ".png"))])
    processed_files = 0

    for file in os.listdir(folder_path):
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            img_path = os.path.join(folder_path, file)

            # Load and preprocess the image
            img = load_and_prep_image(img_path)

            # Make a prediction
            pred = ResNet50V2_Model.predict(np.expand_dims(img, axis=0))

            # Get the predicted class
            pred_class = class_names[pred.argmax()]

            # Count the occurrences of each emotion
            if pred_class in emotions_count:
                emotions_count[pred_class] += 1
            else:
                emotions_count[pred_class] = 1

            # Store the image for each emotion
            if pred_class in emotions_images:
                emotions_images[pred_class].append(img_path)
            else:
                emotions_images[pred_class] = [img_path]

            # Update the progress and send it to the frontend
            processed_files += 1
            progress = processed_files / total_files * 100
            print(progress)
            progress_callback(progress)

    # Determine the emotion with the highest count
    final_emotion = max(emotions_count, key=emotions_count.get)

    return final_emotion, emotions_images


def load_and_prep_image(filename, img_shape=224):
    img = cv2.imread(filename)

    GrayImg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = faceCascade.detectMultiScale(GrayImg, 1.1, 4)

    for x, y, w, h in faces:

        roi_GrayImg = GrayImg[y: y + h, x: x + w]
        roi_Img = img[y: y + h, x: x + w]

        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        faces = faceCascade.detectMultiScale(roi_Img, 1.1, 4)

        if len(faces) == 0:
            print("No Faces Detected")
        else:
            for (ex, ey, ew, eh) in faces:
                img = roi_Img[ey: ey + eh, ex: ex + ew]

    RGBImg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    RGBImg = cv2.resize(RGBImg, (img_shape, img_shape))

    RGBImg = RGBImg / 255.

    return RGBImg


if __name__ == '__main__':
    app.run(debug=True)
