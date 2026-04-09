import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re
import os
import PyPDF2
import asyncio
import edge_tts
import json
import traceback

# --- CUSTOM BEAUTIFUL FONT & CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

/* 1. Make the overall container transparent and wider */
.block-container {
    max-width: 90% !important; 
    padding: 2rem !important;
    background: transparent !important; 
}

/* 2. Apply the white box design ONLY to the main left column */
[data-testid="column"]:nth-of-type(1) {
    background: rgba(255, 255, 255, 0.9);
    border-radius: 20px;
    padding: 2.5rem;
}

/* Reset nested columns (like logo, flashcards) so they don't get double white boxes */
[data-testid="column"] [data-testid="column"] {
    background: transparent !important;
    padding: 0 !important;
}

/* Background pattern */
.stApp {
    background-image: url("https://www.transparenttextures.com/patterns/white-diamond.png");
    background-color: #fff5f7;
    background-attachment: fixed;
}
html, body, p, h1, h2, h3, span {
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stExpander"] svg {
    display: none !important;
}
[data-testid="stIconMaterial"] {
    display: none !important;
    width: 0px !important;
}
[data-testid="stExpander"] details summary {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    text-align: center !important;
}
[data-testid="stExpander"] details summary p {
    flex-grow: 0 !important;
    margin: 0 auto !important;
    font-weight: 600 !important;
}

/* Quiz styling */
.correct-answer { color: green; font-weight: bold; }
.wrong-answer { color: red; font-weight: bold; }

/* Make Tab Headings Smaller & Sleeker */
button[data-baseweb="tab"] p {
    font-size: 16px !important; 
    font-weight: 600 !important; 
}
button[data-baseweb="tab"] {
    padding-top: 10px !important; 
    padding-bottom: 10px !important; 
}
button[data-baseweb="tab"][aria-selected="true"] p {
    color: #4b0082 !important; 
}
div[data-baseweb="tab-highlight"] {
    background-color: #4b0082 !important; 
}

/* Style the action buttons */
button[kind="secondary"] {
    border-radius: 10px !important;
    border: 1px solid #FFB6C1 !important; 
    transition: all 0.3s ease !important;
    white-space: normal !important; 
    min-height: 70px !important;    
    width: 100% !important;         
}
button[kind="secondary"]:hover {
    background-color: #ffe4e1 !important; 
    border-color: #D81B60 !important; 
    transform: translateY(-2px); 
} 
            
    light_pastel_colors = [

        {"bg": "#FFE4E1", "border": "#FFB6C1", "text": "#D81B60"}, 

        {"bg": "#E0FFFF", "border": "#B0E0E6", "text": "#008B8B"}

    ]

    dark_card_colors = [

        {"bg": "#2a1e28", "border": "#d81b60", "text": "#ffb6c1"}, 

        {"bg": "#1e2a2a", "border": "#008b8b", "text": "#b0e0e6"}

    ]
</style>
""", unsafe_allow_html=True)

# --- STRICTLY SEPARATED & PERSISTENT SESSION STATE ---
state_defaults = {
    "yt_data": {'notes': None, 'podcast_audio': None, 'podcast_script': None, 'quiz': None},
    "yt_order": [],
    "yt_flashcards": [],
    "yt_card_idx": 0,
    "yt_quiz_submitted": False,
    "current_vid": None, 
    
    "pdf_data": {'notes': None, 'podcast_audio': None, 'podcast_script': None, 'quiz': None},
    "pdf_order": [],
    "pdf_flashcards": [],
    "pdf_card_idx": 0,
    "pdf_quiz_submitted": False,
    "current_pdf": None, 
    
    "txt_data": {'notes': None, 'podcast_audio': None, 'podcast_script': None, 'quiz': None},
    "txt_order": [],
    "txt_flashcards": [],
    "txt_card_idx": 0,
    "txt_quiz_submitted": False,

    # Global tracking and Mini-Tutor States
    "active_mode": None,
    "active_context": "",
    "chat_history": [],

    "dark_mode": False
}

for key, value in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

for key, value in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --- EXHAUSTIVE PURE DARK MODE OVERRIDE ---
if st.session_state.dark_mode:
    st.markdown("""
    <style>
    /* 1. Main Backgrounds (App & Header) -> Softer Greyish-Black */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #202124 !important; 
        background-image: none !important;
    }
    
    /* 2. The Sidebar (Mini-Tutor) -> Medium Grey */
    [data-testid="stSidebar"], [data-testid="stSidebarHeader"] {
        background-color: #2d2e33 !important;
        background-image: none !important;
    }
    
    /* 3. The Main Box -> Slightly elevated grey */
    [data-testid="column"]:nth-of-type(1) {
        background-color: #28292e !important;
        border: 1px solid #444 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }

    /* 4. Force ALL Text to be standard grey/white */
    html, body, p, h1, h2, h3, h4, h5, h6, span, label, li, .stMarkdown {
        color: #e8eaed !important;
    }
    .main-title { color: #ffffff !important; } 
    
    /* 5. Fix Text Inputs & Chat Inputs (Kill the pink outlines) */
    div[data-baseweb="base-input"], 
    div[data-baseweb="base-input"] > input, 
    div[data-baseweb="base-input"] > textarea,
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] {
        background-color: #3b3c40 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: 1px solid #5f6368 !important;
    }
    /* Force focus state to be white/grey instead of pink */
    div[data-baseweb="base-input"]:focus-within {
        border-color: #e8eaed !important; 
    }

    /* 6. Tabs (Pure grey/white, no purple) */
    button[data-baseweb="tab"] p { color: #9aa0a6 !important; }
    button[data-baseweb="tab"][aria-selected="true"] p { color: #ffffff !important; }
    div[data-baseweb="tab-highlight"] { background-color: #ffffff !important; }
    
    /* 7. ALL Buttons -> Pure Grey */
    button[kind="secondary"], button[kind="primary"], button[kind="primaryFormSubmit"] {
        background-color: #303136 !important;
        border: 1px solid #5f6368 !important;
        color: #e8eaed !important;
    }
    button[kind="secondary"]:hover, button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
        border-color: #e8eaed !important;
        background-color: #44464d !important;
        color: #ffffff !important;
    }
    
    /* 8. Chat Bubbles in Mini-Tutor */
    [data-testid="stChatMessage"] {
        background-color: #3b3c40 !important;
        border-radius: 10px;
    }
    
    /* 9. Informational boxes (Overrides Streamlit's default colors) */
    [data-testid="stAlert"], [data-testid="stNotification"] {
        background-color: #3b3c40 !important;
        color: #e8eaed !important;
        border: 1px solid #5f6368 !important;
    }

    /* 10. Kill Streamlit's default pink Toggle switch track */
    div[data-testid="stToggle"] div[data-baseweb="checkbox"] > div {
        background-color: #5f6368 !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURATION ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

pastel_colors = [
    {"bg": "#FFE4E1", "border": "#FFB6C1", "text": "#D81B60"}, 
    {"bg": "#E0FFFF", "border": "#B0E0E6", "text": "#008B8B"}, 
    {"bg": "#F0FFF0", "border": "#98FB98", "text": "#2E8B57"}, 
    {"bg": "#FFFACD", "border": "#F0E68C", "text": "#B8860B"}, 
    {"bg": "#E6E6FA", "border": "#D8BFD8", "text": "#8A2BE2"}  
]

# --- HELPER FUNCTIONS ---
def generate_study_guide(text_input):
    prompt = f"You are an expert professor. Create a study guide for:\n{text_input}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            st.error("🛑 **API Limit Hit!** Please wait 60 seconds. The Free Tier is currently full.")
            return "Unable to generate notes right now due to API limits. Try again in a minute!"
        return f"Error: {e}"

def generate_flashcards(text_input):
    prompt = "Create exactly 15 effective study flashcards based ONLY on the following text. Format exactly as: \n**Q:** [Question]\n**A:** [Answer]\nUse '---' to separate cards.\nText:\n"
    return model.generate_content(prompt + text_input).text

def parse_flashcards(raw_text):
    cards = []
    blocks = raw_text.split('---')
    for block in blocks:
        q_match = re.search(r'\*\*Q:\*\*\s*(.+)', block)
        a_match = re.search(r'\*\*A:\*\*\s*(.+)', block)
        if q_match and a_match:
            cards.append({'q': q_match.group(1).strip(), 'a': a_match.group(1).strip()})
    return cards

def generate_quiz(text_input):
    prompt = """You are an expert test creator. Generate exactly 15 multiple-choice questions based ONLY on the provided text.
    Return ONLY a raw JSON array. Do not use markdown formatting blocks like ```json. 
    Format exactly like this:
    [
      {"q": "Question?", "options": ["A", "B", "C", "D"], "answer": "A"}
    ]
    Text: """
    response = model.generate_content(prompt + text_input)
    try:
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        return None

def ask_mini_tutor(question, context):
    prompt = f"You are a friendly, helpful AI tutor. Answer based strictly on context.\n\nContext:\n{context}\n\nQuestion:\n{question}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ **AI is overwhelmed!** Google's free tier only allows a few requests per minute. Please wait 30 seconds and try again."
        return f"❌ Error: {str(e)}"

def generate_podcast_script(text_input, language="English"):
    prompt = f"Turn the following text into a highly engaging podcast script between two AI hosts. Entire script MUST be in {language}. Keep the labels exactly as 'Alex:' and 'Sam:' in English. Text:\n"
    return model.generate_content(prompt + text_input).text

def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en', 'en-IN'])
        return " ".join([d['text'] for d in transcript_data])
    except Exception as e:
        return str(e)

def run_podcast_generation(source_text, language="English"):
    with st.spinner(f"✍️ AI is writing your Quick Learn podcast in {language}..."):
        try:
            podcast_script = generate_podcast_script(source_text, language)
            
            sam_voice = "hi-IN-MadhurNeural" if language == "Hindi" else "en-US-GuyNeural"
            alex_voice = "hi-IN-SwaraNeural" if language == "Hindi" else "en-US-AriaNeural"

            with st.spinner("⚡ Recording audio... (This takes a moment!)"):
                async def generate_all_audio_sequentially(lines_data):
                    for filename, text, voice, speaker in lines_data:
                        try:
                            communicate = edge_tts.Communicate(text, voice)
                            await communicate.save(filename)
                            await asyncio.sleep(0.2) 
                        except Exception as e:
                            raise e 

                audio_files, lines_data = [], []
                lines = [line for line in podcast_script.split('\n') if line.strip()]
                
                for i, line in enumerate(lines):
                    clean_line = line.replace("**", "").replace("*", "").strip()
                    if clean_line.startswith("Sam:") or clean_line.startswith("सैम:"):
                        text_only = clean_line.split(":", 1)[1].strip()
                        if len(text_only) > 1: 
                            filename = f"line_{i}.mp3"
                            lines_data.append((filename, text_only, sam_voice, "Sam"))
                            audio_files.append(filename)
                    elif clean_line.startswith("Alex:") or clean_line.startswith("एलेक्स:"):
                        text_only = clean_line.split(":", 1)[1].strip()
                        if len(text_only) > 1: 
                            filename = f"line_{i}.mp3"
                            lines_data.append((filename, text_only, alex_voice, "Alex"))
                            audio_files.append(filename)

                if lines_data:
                    asyncio.run(generate_all_audio_sequentially(lines_data))

                with open("final_podcast.mp3", "wb") as outfile:
                    for file in audio_files:
                        if os.path.exists(file):
                            with open(file, "rb") as infile: outfile.write(infile.read())
                            try: os.remove(file)
                            except: pass 

                with open("final_podcast.mp3", "rb") as f:
                    audio_bytes = f.read()
                    
                try: os.remove("final_podcast.mp3")
                except: pass
                    
                return audio_bytes, lines
                
        except Exception as e:
            st.error(f"A backend error occurred: {e}")
            return None, None

# --- UI RENDER HELPERS ---
def update_order(tab_prefix, item_type):
    if item_type in st.session_state[f"{tab_prefix}_order"]:
        st.session_state[f"{tab_prefix}_order"].remove(item_type)
    st.session_state[f"{tab_prefix}_order"].insert(0, item_type)

def render_guide_ui(tab_prefix, title_text):
    st.markdown("---")
    st.markdown(f"### {title_text}")
    content = st.session_state[f"{tab_prefix}_data"]['notes']
    st.markdown(content)

def render_flashcards_ui(tab_prefix):
    st.markdown("---")
    st.markdown(f"### 🗂️ Your Flashcards")
    cards = st.session_state[f"{tab_prefix}_flashcards"]
    idx_key = f"{tab_prefix}_card_idx"
    idx = st.session_state[idx_key]
    
    if not cards:
        st.warning("No flashcards found. Please generate them again.")
        return

    if idx >= len(cards): st.session_state[idx_key] = 0; idx = 0
    
    # --- THIS IS THE STEP 3 MAGIC ---
    # We define both color palettes right here so they are easy to manage
    light_pastel_colors = [
        {"bg": "#FFE4E1", "border": "#FFB6C1", "text": "#D81B60"}, 
        {"bg": "#E0FFFF", "border": "#B0E0E6", "text": "#008B8B"}, 
        {"bg": "#F0FFF0", "border": "#98FB98", "text": "#2E8B57"}, 
        {"bg": "#FFFACD", "border": "#F0E68C", "text": "#B8860B"}, 
        {"bg": "#E6E6FA", "border": "#D8BFD8", "text": "#8A2BE2"}  
    ]

    dark_card_colors = [
        {"bg": "#2a1e28", "border": "#d81b60", "text": "#ffb6c1"}, 
        {"bg": "#1e2a2a", "border": "#008b8b", "text": "#b0e0e6"}, 
        {"bg": "#1e2a20", "border": "#2e8b57", "text": "#98fb98"}, 
        {"bg": "#2a281e", "border": "#b8860b", "text": "#f0e68c"}, 
        {"bg": "#221e2a", "border": "#8a2be2", "text": "#d8bfd8"}  
    ]

    # Check the toggle and pick the right list of colors
    current_colors = dark_card_colors if st.session_state.dark_mode else light_pastel_colors
    color = current_colors[idx % len(current_colors)]
    
    # Force the main question text to be white in dark mode, dark grey in light mode
    card_text_color = "#e0e0e0" if st.session_state.dark_mode else "#333333"

    # Draw the actual card
    st.markdown(f"**Card {idx + 1} of {len(cards)}**")
    st.markdown(f"""
    <div style="background-color: {color['bg']}; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid {color['border']}; transition: all 0.3s ease;">
        <p style="font-weight: bold; margin: 0; color: {color['text']};">Question</p>
        <p style="margin: 5px 0 0 0; color: {card_text_color}; font-size: 16px;">{cards[idx]['q']}</p>
    </div>
    """, unsafe_allow_html=True)
    # --- END OF STEP 3 MAGIC ---
    
    with st.expander("💡 View Answer"):
        st.markdown(f"**Answer:** {cards[idx]['a']}")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Prev", disabled=(idx == 0), key=f"prev_{tab_prefix}", use_container_width=True):
            st.session_state[idx_key] -= 1
            st.rerun()
    with col3:
        if st.button("Next ➡️", disabled=(idx == len(cards) - 1), key=f"next_{tab_prefix}", use_container_width=True):
            st.session_state[idx_key] += 1
            st.rerun()

def render_quiz_ui(tab_prefix):
    st.markdown("---")
    st.markdown("### 📝 Practice Quiz")
    quiz_data = st.session_state[f"{tab_prefix}_data"]['quiz']
    
    if not quiz_data:
        st.warning("Quiz data could not be loaded. Please try generating it again.")
        return

    with st.form(key=f"quiz_form_{tab_prefix}"):
        user_answers = {}
        for i, q in enumerate(quiz_data):
            st.markdown(f"**Q{i+1}: {q['q']}**")
            user_answers[i] = st.radio(
                "Options", 
                q['options'], 
                key=f"radio_{tab_prefix}_{i}", 
                label_visibility="collapsed",
                index=None
            )
            st.write("")
        
        submit_quiz = st.form_submit_button("✅ Submit Answers")
        
        if submit_quiz:
            st.session_state[f"{tab_prefix}_quiz_submitted"] = True

    if st.session_state.get(f"{tab_prefix}_quiz_submitted", False):
        score = 0
        st.markdown("#### Quiz Results")
        for i, q in enumerate(quiz_data):
            user_ans = user_answers[i]
            correct_ans = q['answer']
            if user_ans == correct_ans:
                score += 1
                st.success(f"**Q{i+1}:** Correct! ({correct_ans})")
            else:
                st.error(f"**Q{i+1}:** Incorrect. You chose '{user_ans}'. The correct answer is **{correct_ans}**.")
        st.markdown(f"### Final Score: {score} / {len(quiz_data)}")

def render_podcast_ui(tab_prefix):
    st.markdown("---")
    st.markdown("### 🎧 AI Podcast")
    st.audio(st.session_state[f"{tab_prefix}_data"]['podcast_audio'], format="audio/mp3")
    with st.expander("📝 View Podcast Script"):
        for line in st.session_state[f"{tab_prefix}_data"]['podcast_script']:
            clean = line.replace("**", "").replace("*", "").strip()
            if clean.startswith("Sam:") or clean.startswith("सैम:"): st.write(f"🧑‍🏫 **Sam:** {clean.split(':', 1)[1].strip()}")
            elif clean.startswith("Alex:") or clean.startswith("एलेक्स:"): st.write(f"🎧 **Alex:** {clean.split(':', 1)[1].strip()}")

# --- SIDEBAR: MINI-TUTOR ---
with st.sidebar:

    st.toggle("🌙 Dark Mode", key="dark_mode")
    st.markdown("---")

    st.markdown("## ☁️ Mini-Tutor")
    if not st.session_state.active_context:
        st.info("Upload a doc or paste a link first! I will read the material instantly and be ready to answer your questions.")
    else:
        st.success("🧠 Material loaded! Ask me anything about it.")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        if prompt := st.chat_input("I'm confused about..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = ask_mini_tutor(prompt, st.session_state.active_context)
                    st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

# --- MAIN APP LAYOUT ---
st.set_page_config(page_title="BingeLearn", page_icon="🎓", layout="wide")
# 1. Initialize dark mode state if it doesn't exist
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# 1. NEW TOP-LEVEL COLUMNS
main_box, right_margin = st.columns([7.5, 2.5], gap="large")

# 2. EVERYTHING INSIDE THE WHITE BOX GOES HERE
with main_box:
    # Slightly adjusted the column ratio so the logo isn't squeezed
    col1, col2 = st.columns([1.2, 8.8]) 
    
    with col1: 
        # This invisible spacer pushes the logo down just enough to stop the top from cropping
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        st.image("logo.png", width=200) 
        
    with col2: 
        # Added 'class="main-title"' so dark mode can turn it white, and adjusted padding to align with the logo
        st.markdown('<h1 class="main-title" style="margin-top: 0px; padding-top: 20px; color: #4b0082;">BingeLearn</h1>', unsafe_allow_html=True)

    st.write("Turn long educational videos, PDFs, and your own notes into instant, downloadable study cheat sheets & podcasts.")

    tab1, tab2, tab3 = st.tabs(["📺 YouTube Video", "📄 PDF Document", "✍️ Blank Document"])

    # --- TAB 1: YOUTUBE ---
    with tab1:
        # Note: No columns here anymore, input takes full width of the white box!
        youtube_url = st.text_input("Paste a YouTube Video URL here:")
        if youtube_url:
            vid_id = extract_video_id(youtube_url)
            if vid_id and st.session_state.current_vid != vid_id:
                transcript = get_transcript(vid_id)
                if len(transcript) > 50 and "Could not retrieve" not in transcript:
                    st.session_state.active_context = transcript
                    st.session_state.current_vid = vid_id
                    st.session_state.active_mode = 'yt'
                else:
                    st.error("Transcript missing or too short.")
            elif vid_id == st.session_state.current_vid:
                st.session_state.active_mode = 'yt' # Keep active if clicked back to tab

        for item in st.session_state.yt_order:
            if item == 'notes': render_guide_ui('yt', '📚 YouTube Study Guide')
            elif item == 'flashcards': render_flashcards_ui('yt')
            elif item == 'quiz': render_quiz_ui('yt')
            elif item == 'podcast': render_podcast_ui('yt')

    # --- TAB 2: PDF ---
    with tab2:
        uploaded_pdf = st.file_uploader("Upload your PDF document", type=["pdf"])
        if uploaded_pdf:
            if st.session_state.current_pdf != uploaded_pdf.name:
                pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
                extracted = "".join([page.extract_text() + "\n" for page in pdf_reader.pages if page.extract_text()])
                if len(extracted) > 50:
                    st.session_state.active_context = extracted
                    st.session_state.current_pdf = uploaded_pdf.name
                    st.session_state.active_mode = 'pdf'
            elif uploaded_pdf.name == st.session_state.current_pdf:
                st.session_state.active_mode = 'pdf'

        for item in st.session_state.pdf_order:
            if item == 'notes': render_guide_ui('pdf', '📝 PDF Notes')
            elif item == 'flashcards': render_flashcards_ui('pdf')
            elif item == 'quiz': render_quiz_ui('pdf')
            elif item == 'podcast': render_podcast_ui('pdf')

    # --- TAB 3: TEXT ---
    with tab3:
        user_text_input = st.text_area("Dump your raw notes, text, or ideas here...", height=200)
        if len(user_text_input) > 50:
            st.session_state.active_context = user_text_input
            st.session_state.active_mode = 'txt'

        for item in st.session_state.txt_order:
            if item == 'notes': render_guide_ui('txt', '✨ Structured Notes')
            elif item == 'flashcards': render_flashcards_ui('txt')
            elif item == 'quiz': render_quiz_ui('txt')
            elif item == 'podcast': render_podcast_ui('txt')

# 3. GLOBAL BUTTONS OUTSIDE THE WHITE BOX
with right_margin:
    # Push buttons down slightly so they visually align with the content area
    st.write("") 
    st.write("")
    st.write("")
    st.write("")
    
    # Optional indicator to let you know which tab the buttons are targeting
    mode_map = {"yt": "📺 Video", "pdf": "📄 PDF", "txt": "✍️ Text"}
    active_m = st.session_state.get("active_mode")
    if active_m:
        st.caption(f"**Targeting:** {mode_map[active_m]}")

    btn_guide = st.button("📚 Study Guide", use_container_width=True)
    btn_flash = st.button("🗂️ Flashcards", use_container_width=True)
    btn_quiz  = st.button("📝 Practice Quiz", use_container_width=True)
    
    with st.popover("🎧 Podcast", use_container_width=True):
        pod_lang = st.radio("Language", ["English", "Hindi"], horizontal=True, label_visibility="collapsed")
        btn_pod  = st.button("🚀 Start Audio", use_container_width=True)

    # --- UNIFIED BUTTON LOGIC ---
    if btn_guide or btn_flash or btn_quiz or btn_pod:
        mode = st.session_state.get("active_mode")
        context = st.session_state.get("active_context")
        
        if not mode or not context:
            st.warning("Please paste a link, upload a PDF, or add text in the main window first!")
        else:
            if btn_guide:
                with st.spinner("📚 Analyzing..."):
                    st.session_state[f"{mode}_data"]['notes'] = generate_study_guide(context)
                    update_order(mode, "notes")
                    st.rerun() # Forces the main UI to update immediately
                    
            elif btn_flash:
                with st.spinner("🗂️ Generating..."):
                    parsed = parse_flashcards(generate_flashcards(context))
                    if parsed: 
                        st.session_state[f"{mode}_flashcards"] = parsed
                        st.session_state[f"{mode}_card_idx"] = 0
                        update_order(mode, "flashcards")
                        st.rerun()
                        
            elif btn_quiz:
                with st.spinner("📝 Creating quiz..."):
                    quiz = generate_quiz(context)
                    if quiz: 
                        st.session_state[f"{mode}_data"]['quiz'] = quiz
                        st.session_state[f"{mode}_quiz_submitted"] = False
                        update_order(mode, "quiz")
                        st.rerun()
                        
            elif btn_pod:
                audio, script = run_podcast_generation(context, language=pod_lang)
                if audio: 
                    st.session_state[f"{mode}_data"]['podcast_audio'] = audio
                    st.session_state[f"{mode}_data"]['podcast_script'] = script
                    update_order(mode, "podcast")
                    st.rerun()