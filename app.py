import streamlit as st
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
import os
from dotenv import load_dotenv
import requests  # For weather API
from PIL import Image  # For image upload handling
import time  # For animations

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

def analyze_crop_image(uploaded_file):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        image = Image.open(uploaded_file)
        prompt = "Analyze this crop image for diseases, pests, or issues. Provide detailed diagnosis, remedies, and prevention tips as AgriSense for SIH."
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

def get_market_price(crop):
    # Placeholder for API (e.g., Agmarknet or custom API)
    return f"Market Price for {crop}: Approx. ₹50/kg (Check local markets for real-time data)"

# ---------------------------
# CUSTOM CSS FOR ENHANCED AESTHETICS
# ---------------------------
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%);  /* Blue-to-green gradient */
        font-family: 'Arial', sans-serif;
        color: black;
        animation: fadeIn 1s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .user-message {
        background-color: #FF9F55;  /* Warm orange */
        color: black;
        padding: 15px;
        border-radius: 20px;
        margin: 10px;
        max-width: 80%;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.2);
        font-size: 16px;
    }
    .assistant-message {
        background-color: #6A1B9A;  /* Deep purple */
        color: white;  /* White for contrast on dark background */
        padding: 15px;
        border-radius: 20px;
        margin: 10px;
        max-width: 80%;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.2);
        font-size: 16px;
    }
    .stTextArea > div > div > textarea {
        border: 2px solid #FF9F55;
        border-radius: 15px;
        padding: 20px;
        color: #333333;  /* Dark gray for visibility against light background */
        background-color: rgba(255, 255, 255, 0.9);  /* Semi-transparent white background */
        font-size: 18px;
        height: 150px;  /* Increased height */
        width: 100%;  /* Full width in wide layout */
    }
    .stButton > button {
        background: linear-gradient(135deg, #FF9F55, #6A1B9A);
        color: white;  /* White for contrast */
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
        color: #FFD700;  /* Bright gold */
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
    page_title="AgriSense — AI Farming Assistant (SIH)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# SIDEBAR FOR ENHANCED FEATURES
# ---------------------------
st.sidebar.title("🌾 AgriSense Control Panel")
st.sidebar.markdown("**Smart India Hackathon (SIH) Edition**")
st.sidebar.markdown("### Quick Tools")
if st.sidebar.button("🌤️ Weather"):
    city = st.sidebar.text_input("City:", "Mumbai")
    weather = get_weather(city)
    st.sidebar.info(weather)

st.sidebar.markdown("### Crop & Soil Tools")
season = st.sidebar.selectbox("Season:", ["Summer", "Winter", "Monsoon"])
soil = st.sidebar.selectbox("Soil Type:", ["Sandy", "Loamy", "Clayey"])
irrigation = st.sidebar.selectbox("Irrigation:", ["Low", "Moderate", "High"])
if st.sidebar.button("Crop Advice"):
    rec = get_crop_recommendation(season, soil, irrigation)
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
language = st.sidebar.selectbox("Language:", ["English", "Hindi", "Telugu"])
st.sidebar.markdown("### SIH Info")
st.sidebar.markdown("""
- **Team**: AgriSense Innovators
- **Focus**: Farmer Empowerment, AI-Driven Insights
- **Features**: Chat, Voice, Image, Weather, Soil, Market
- **Innovation**: Scalable, Offline-Ready, Multi-Lingual
""")

# ---------------------------
# HEADER
# ---------------------------
st.markdown("""
    <h1 style='text-align: center;'>
        🌱 AgriSense — AI Farming Assistant (SIH 2025)
    </h1>
    <p style='text-align: center;'>
        Empowering Farmers with AI: Chat, Voice, Image Analysis, Weather, Soil & Market Insights! 🌾🚀
    </p>
    <hr style='border-color: #FFD700; border-width: 2px;'>
""", unsafe_allow_html=True)

# ---------------------------
# DASHBOARD (SIH Expansion)
# ---------------------------
st.subheader("📊 Farmer Dashboard")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="dashboard-metric">Users Today: 150</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="dashboard-metric">Weather Alerts: 5</div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="dashboard-metric">Queries Solved: 200</div>', unsafe_allow_html=True)

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
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)
    if st.button("Analyze Image"):
        analysis = analyze_crop_image(uploaded_file)
        st.markdown(f'<div class="assistant-message">{analysis}</div>', unsafe_allow_html=True)
        speak(analysis)

# ---------------------------
# SESSION STATE
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello 👋 I’m AgriSense, your SIH-powered farming assistant. Ask about crops, weather, soil, or upload images! How can I assist?"}
    ]

# ---------------------------
# SPEECH-TO-TEXT FUNCTION
# ---------------------------
def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Listening... speak now!")
        audio = r.listen(source)
        try:
            return r.recognize_google(audio)
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand your voice."
        except sr.RequestError:
            return "Sorry, voice service is down."

# ---------------------------
# GET RESPONSE FROM GEMINI
# ---------------------------
def get_ai_response(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are AgriSense, an advanced AI farming assistant for SIH 2025. Provide detailed, expert advice on crops, weather impacts, soil health, pest control, market trends, and general agriculture queries. Include practical remedies and local context (e.g., India, 08:23 PM IST, Sep 15, 2025). Respond in a friendly, authoritative tone.\nUser: {prompt}"
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

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
# INPUT AREA
# ---------------------------
st.markdown("### 💬 Ask Your Detailed Question")
user_input = st.text_area("You:", "", key="text_input", placeholder="Enter a detailed query... e.g., 'How to manage banana leaf spot in monsoon with loamy soil in India?'", height=150)

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Send 🚀", key="send_button"):
        if user_input.strip():
            st.session_state.messages.append({"role": "user", "content": user_input})
            reply = get_ai_response(user_input)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            speak(reply)
            st.rerun()

with col2:
    if st.button("🎤 Speak", key="speak_button"):
        voice_text = recognize_speech()
        if voice_text:
            st.session_state.messages.append({"role": "user", "content": voice_text})
            reply = get_ai_response(voice_text)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            speak(reply)
            st.rerun()

# ---------------------------
# TEAM COLLABORATION (SIH Expansion)
# ---------------------------
st.subheader("🤝 Team AgriSense")
st.markdown("""
- **Leader**: [Your Name]
- **Members**: [Member1, Member2, Member3]
- **Tasks**: AI Integration, UI Design, Data Collection
- **Status**: In Progress (Update live during SIH)
""")

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("""
    <hr style='border-color: #FFD700; border-width: 2px;'>
    <p style='text-align: center; color: black; font-size: 14px;'>
        🌟 AgriSense | Smart India Hackathon 2025 | Empowering Farmers with AI 🚀 | © 2025 Team AgriSense
    </p>
""", unsafe_allow_html=True)