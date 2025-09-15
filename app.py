import streamlit as st
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
import os
from dotenv import load_dotenv
import requests
from PIL import Image
import sqlite3
import time

# ---------------------------
# LOAD ENV FILE (for API Keys)
# ---------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY not found in .env file. Please set it up.")
    st.stop()
genai.configure(api_key=api_key)

weather_api_key = os.getenv("OPENWEATHER_API_KEY")
if not weather_api_key:
    st.warning("OPENWEATHER_API_KEY not set. Weather feature limited.")

# ---------------------------
# DATABASE SETUP
# ---------------------------
conn = sqlite3.connect('agrisense.db', check_same_thread=False)
c = conn.cursor()

# Create tables if not exist
c.execute('''CREATE TABLE IF NOT EXISTS chats
             (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, role TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
c.execute('''CREATE TABLE IF NOT EXISTS alerts
             (id INTEGER PRIMARY KEY AUTOINCREMENT, alert_type TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

# ---------------------------
# TEXT-TO-SPEECH ENGINE INITIALIZATION
# ---------------------------
engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    try:
        if engine._inLoop:
            engine.endLoop()
        engine.say(text)
        engine.runAndWait()
    except RuntimeError as e:
        st.warning(f"Text-to-speech error: {str(e)}. Retrying...")
        engine.endLoop()
        engine.say(text)
        engine.runAndWait()

# ---------------------------
# EMAIL FUNCTION (Optional)
# ---------------------------
def send_email(to_email, subject, body):
    try:
        smtp_server = st.secrets.get("smtp", {}).get("server")
        smtp_port = st.secrets.get("smtp", {}).get("port")
        sender_email = st.secrets.get("smtp", {}).get("sender")
        sender_password = st.secrets.get("smtp", {}).get("password")

        if not all([smtp_server, smtp_port, sender_email, sender_password]):
            st.warning("Email functionality disabled: SMTP secrets not found. Check secrets.toml.")
            return False

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

# ---------------------------
# ENHANCED FUNCTIONS
# ---------------------------
def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            return f"Weather in {city}: {data['weather'][0]['description']}, Temp: {data['main']['temp']}°C, Humidity: {data['main']['humidity']}%"
        return "City not found or API error."
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

def get_crop_recommendation(season, soil_type, irrigation):
    recommendations = {
        "summer": {"sandy": {"crops": "Cotton, Groundnut", "pests": "Aphids, Bollworms", "irrigation": "Moderate"},
                   "loamy": {"crops": "Maize, Rice", "pests": "Stem Borers", "irrigation": "High"}},
        "winter": {"sandy": {"crops": "Wheat, Gram", "pests": "Rust, Aphids", "irrigation": "Low"},
                   "loamy": {"crops": "Potato, Mustard", "pests": "Blights", "irrigation": "Moderate"}},
        "monsoon": {"sandy": {"crops": "Millets, Pulses", "pests": "Leafhoppers", "irrigation": "Minimal"},
                    "loamy": {"crops": "Paddy, Sugarcane", "pests": "Sheath Blight", "irrigation": "High"}}
    }
    rec = recommendations.get(season.lower(), {}).get(soil_type.lower(), {})
    if rec:
        return f"Crops: {rec['crops']}\nPests: {rec['pests']}\nIrrigation: {rec['irrigation']} (adjust based on {irrigation.lower()})"
    return "General recommendation: Consult local expert."

def analyze_soil_health(nitrogen, phosphorus, potassium):
    health = "Healthy" if all(x > 20 for x in [nitrogen, phosphorus, potassium]) else "Needs Improvement"
    return f"Soil Health: {health}\nNitrogen: {nitrogen}%, Phosphorus: {phosphorus}%, Potassium: {potassium}%\nAdvice: {'Add organic manure' if health == 'Needs Improvement' else 'Maintain current practices'}"

def analyze_crop_image(uploaded_file, language):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        image = Image.open(uploaded_file)
        prompt = f"Analyze this crop image for diseases, pests, or issues. Provide detailed diagnosis, remedies, and prevention tips as AgriSense. Respond in {language}."
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

def get_market_price(crop):
    return f"Market Price for {crop}: Approx. ₹50/kg (Check local markets for real-time data)"

def get_ai_response(prompt, language):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are AgriSense, an advanced AI farming assistant. Provide detailed, expert advice on crops, weather impacts, soil health, pest control, market trends, and general agriculture queries. Include practical remedies and local context (e.g., India, 09:40 PM IST, Sep 15, 2025). Respond in {language} with a friendly, authoritative tone.\nUser: {prompt}"
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ---------------------------
# CUSTOM CSS FOR ENHANCED AESTHETICS
# ---------------------------
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%);
        font-family: 'Arial', sans-serif;
        color: black;
        animation: fadeIn 1s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .user-message {
        background-color: #FF9F55;
        color: black;
        padding: 15px;
        border-radius: 20px;
        margin: 10px;
        max-width: 80%;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.2);
        font-size: 16px;
    }
    .assistant-message {
        background-color: #6A1B9A;
        color: white;
        padding: 15px;
        border-radius: 20px;
        margin: 10px;
        max-width: 80%;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.2);
        font-size: 16px;
    }
    .stTextArea > div > div > textarea, .stChatInput > div > div > textarea {
        border: 2px solid #FF9F55;
        border-radius: 15px;
        padding: 20px;
        color: black;
        background-color: white;
        font-size: 18px;
        height: 150px;
        width: 100%;
    }
    .stButton > button {
        background: linear-gradient(135deg, #FF9F55, #6A1B9A);
        color: white;
        border-radius: 15px;
        padding: 12px 24px;
        font-size: 16px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        transition: transform 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #6A1B9A, #FF9F55);
        transform: scale(1.05);
        color: white;
    }
    h1, h3 {
        color: #FFD700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    p {
        color: black;
        font-size: 16px;
    }
    .feature-card {
        background-color: rgba(255, 255, 255, 0.85);
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }
    .feature-card:hover {
        transform: scale(1.02);
    }
    .dashboard-metric {
        background-color: rgba(106, 27, 154, 0.8);
        color: white;
        padding: 10px;
        border-radius: 10px;
        margin: 5px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="AgriSense — AI Farming Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# INITIALIZE SESSION STATE
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load chat history from DB (general, no user-specific)
c.execute("SELECT role, message FROM chats ORDER BY timestamp ASC")
st.session_state.messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]

# Dashboard metrics (aggregate for all interactions)
c.execute("SELECT COUNT(*) FROM chats WHERE role = 'assistant'")
queries_solved = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM alerts")
weather_alerts = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT DATE(timestamp)) FROM chats")  # Approx users by unique days
users_today = c.fetchone()[0]

# ---------------------------
# DASHBOARD
# ---------------------------
st.subheader("📊 Farmer Dashboard")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="dashboard-metric">Users Today: {users_today}</div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="dashboard-metric">Weather Alerts: {weather_alerts}</div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="dashboard-metric">Queries Solved: {queries_solved}</div>', unsafe_allow_html=True)

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.title("🌾 AgriSense Control Panel")
st.sidebar.markdown("### Quick Tools")
enable_email = st.sidebar.checkbox("Enable Email Alerts (Requires secrets.toml)", value=False)
enable_tts = st.sidebar.checkbox("Enable Text-to-Speech", value=True)  # New TTS toggle
if st.sidebar.button("🌤️ Weather"):
    city = st.sidebar.text_input("City:", "Mumbai")
    weather = get_weather(city)
    st.sidebar.info(weather)
    if weather.startswith("Weather"):
        c.execute("INSERT INTO alerts (alert_type, message) VALUES ('weather', ?)", (weather,))
        conn.commit()
        if enable_email and send_email("default@example.com", "Weather Alert", weather):
            st.sidebar.success("Weather alert emailed!")
        else:
            st.sidebar.warning("Email not sent. Enable email alerts and configure secrets.toml.")

st.sidebar.markdown("### Crop & Soil Tools")
season = st.sidebar.selectbox("Season:", ["Summer", "Winter", "Monsoon"])
soil = st.sidebar.selectbox("Soil Type:", ["Sandy", "Loamy", "Clayey"])
irr = st.sidebar.selectbox("Irrigation:", ["Low", "Moderate", "High"])
if st.sidebar.button("Crop Advice"):
    rec = get_crop_recommendation(season, soil, irr)
    st.sidebar.success(rec)

st.sidebar.markdown("### Soil Health")
n = st.sidebar.number_input("Nitrogen %", 0, 100, 30)
p = st.sidebar.number_input("Phosphorus %", 0, 100, 30)
k = st.sidebar.number_input("Potassium %", 0, 100, 30)
if st.sidebar.button("Analyze Soil"):
    health = analyze_soil_health(n, p, k)
    st.sidebar.info(health)

st.sidebar.markdown("### Market Prices")
crop = st.sidebar.selectbox("Crop:", ["Rice", "Wheat", "Cotton"])
if st.sidebar.button("Check Price"):
    price = get_market_price(crop)
    st.sidebar.warning(price)

st.sidebar.markdown("### Settings")
offline_mode = st.sidebar.checkbox("Offline Mode (Limited Features)")
language = st.sidebar.selectbox("Language:", ["English", "Malayalam", "Hindi", "Telugu"])

# ---------------------------
# HEADER
# ---------------------------
st.markdown("""
    <h1 style='text-align: center;'>
        🌱 AgriSense — AI Farming Assistant
    </h1>
    <p style='text-align: center;'>
        Empowering Farmers with AI: Chat, Voice, Image Analysis, Weather, Soil & Market Insights! 🌾🚀
    </p>
    <hr style='border-color: #FFD700; border-width: 2px;'>
""", unsafe_allow_html=True)

# ---------------------------
# FEATURE CARDS
# ---------------------------
st.subheader("🌟 Key Features")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="feature-card">📷 <strong>Image Analysis</strong><br>Diagnose crop diseases.</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="feature-card">🌤️ <strong>Weather</strong><br>Real-time updates.</div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="feature-card">🌾 <strong>Crop Advice</strong><br>Seasonal recommendations.</div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="feature-card">🌍 <strong>Market</strong><br>Price trends.</div>', unsafe_allow_html=True)

# ---------------------------
# IMAGE UPLOAD SECTION
# ---------------------------
st.subheader("📷 Upload Crop Image for Analysis")
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"], key="image_uploader")
if uploaded_file is not None and "image_processed" not in st.session_state:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)
    if st.button("Analyze Image"):
        analysis = analyze_crop_image(uploaded_file, language)
        st.markdown(f'<div class="assistant-message">{analysis}</div>', unsafe_allow_html=True)
        c.execute("INSERT INTO chats (message, role) VALUES (?, 'assistant')", (analysis,))
        conn.commit()
        if enable_tts:
            speak(analysis)
        st.session_state.image_processed = True
        st.rerun()

# ---------------------------
# CHAT DISPLAY
# ---------------------------
st.subheader("💬 AI Chat Assistant")
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"""
        <div style="text-align: right;">
            <div class="user-message">{message["content"]}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align: left;">
            <div class="assistant-message">{message["content"]}</div>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------
# SINGLE INPUT AREA (Grok-like)
# ---------------------------
st.markdown("### 💬 Ask Your Question")
col_input, col_voice, col_file = st.columns([6, 1, 1])
with col_input:
    user_input = st.chat_input("Type, speak, or upload file here...", key="chat_input")

with col_voice:
    if st.button("🎤"):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("Listening...")
            audio = recognizer.listen(source)
            try:
                voice_text = recognizer.recognize_google(audio)
                user_input = voice_text
                st.info(f"Recognized: {voice_text}")
            except sr.UnknownValueError:
                st.error("Could not understand audio")
            except sr.RequestError as e:
                st.error(f"Error with speech recognition service: {e}")

with col_file:
    uploaded_chat_file = st.file_uploader("", type=["jpg", "png", "jpeg", "pdf"], key="chat_file")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    c.execute("INSERT INTO chats (message, role) VALUES (?, 'user')", (user_input,))
    conn.commit()
    reply = get_ai_response(user_input, language)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    c.execute("INSERT INTO chats (message, role) VALUES (?, 'assistant')", (reply,))
    conn.commit()
    if enable_tts:
        speak(reply)
    st.rerun()

if uploaded_chat_file and "file_processed" not in st.session_state:
    if uploaded_chat_file.type in ["image/jpeg", "image/png"]:
        analysis = analyze_crop_image(uploaded_chat_file, language)
        st.session_state.messages.append({"role": "user", "content": "Uploaded image for analysis"})
        st.session_state.messages.append({"role": "assistant", "content": analysis})
        c.execute("INSERT INTO chats (message, role) VALUES (?, 'user')", ("Uploaded image",))
        c.execute("INSERT INTO chats (message, role) VALUES (?, 'assistant')", (analysis,))
        conn.commit()
        if enable_tts:
            speak(analysis)
        st.session_state.file_processed = True
        st.rerun()

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("""
    <hr style='border-color: #FFD700; border-width: 2px;'>
    <p style='text-align: center; color: black; font-size: 14px;'>
        🌟 AgriSense | Empowering Farmers with AI 🚀 | © 2025 AgriSense
    </p>
""", unsafe_allow_html=True)

conn.close()