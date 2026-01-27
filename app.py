import streamlit as st
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from youtube_search import YoutubeSearch
from youtube_transcript_api import YouTubeTranscriptApi

# 1. LOAD API KEY SECURELY
load_dotenv() # This loads variables from .env file
api_key = os.getenv("UPSTAGE_API_KEY")

# Check if key exists
if not api_key:
    st.error("UPSTAGE_API_KEY not found! Please check your .env file.")
    st.stop()

# 2. SETUP UPSTAGE CLIENT
client = OpenAI(
    api_key=api_key,
    base_url="https://api.upstage.ai/v1/solar"
)

# --- LOGIC FUNCTIONS ---

def find_youtube_video(query):
    """Searches YouTube and returns video ID, Title, and Thumbnail."""
    results = YoutubeSearch(query, max_results=1).to_dict()
    if not results:
        return None
    return {
        "id": results[0]['id'],
        "title": results[0]['title'],
        "thumb": results[0]['thumbnails'][0]
    }

def get_video_transcript(video_id):
    """Fetches transcript."""
    try:
        return YouTubeTranscriptApi.get_transcript(video_id)
    except Exception:
        return None

def analyze_transcript_with_upstage(user_query, transcript):
    """Uses Upstage Solar to find the timestamp."""
    
    # Format transcript with timestamps
    formatted_text = ""
    for entry in transcript:
        formatted_text += f"[{int(entry['start'])}s] {entry['text']}\n"
    
    # Truncate to avoid context limits (approx 20 mins of video text)
    formatted_text = formatted_text[:25000]

    system_prompt = (
        "You are a helpful assistant. You will be provided with a user question and a "
        "video transcript with timestamps like [120s]. "
        "Your goal is to identify the best timestamp (in seconds) where the answer begins. "
        "Return ONLY the integer number. Do not return words."
    )

    user_prompt = f"""
    Question: {user_query}
    
    Transcript:
    {formatted_text}
    
    At what second does the answer start? Return only the number.
    """

    try:
        response = client.chat.completions.create(
            model="solar-1-mini-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        answer = response.choices[0].message.content.strip()
        
        # Extract number using Regex just in case Solar adds text
        numbers = re.findall(r'\d+', answer)
        if numbers:
            return int(numbers[0])
        return 0
    except Exception as e:
        st.error(f"AI Error: {e}")
        return 0

# --- STREAMLIT UI ---

st.set_page_config(page_title="YouTube Smart Search", page_icon="📺")

st.title("📺 YouTube Specific Answer Finder")
st.write("Ask a question, and I'll find the exact moment in a YouTube video that answers it.")

# Input
query = st.text_input("What are you looking for?", placeholder="e.g., Best tires for family SUV")

if st.button("Search & Analyze", type="primary"):
    if not query:
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Searching YouTube..."):
            video_data = find_youtube_video(query)
            
        if not video_data:
            st.error("No videos found on YouTube for that query.")
        else:
            st.success(f"Found video: **{video_data['title']}**")
            
            with st.spinner("Downloading transcript and analyzing with Upstage AI..."):
                transcript = get_video_transcript(video_data['id'])
                
                if not transcript:
                    st.warning("This video doesn't have captions. I can't analyze it, but here is the video:")
                    st.video(f"https://www.youtube.com/watch?v={video_data['id']}")
                else:
                    # AI Analysis
                    timestamp = analyze_transcript_with_upstage(query, transcript)
                    
                    # Create Link
                    video_link = f"https://www.youtube.com/watch?v={video_data['id']}&t={timestamp}s"
                    
                    st.divider()
                    st.markdown(f"### 🎯 Answer found at {timestamp} seconds")
                    
                    # Display the video starting at the specific time
                    st.video(video_link, start_time=timestamp)
                    
                    st.markdown(f"**Direct Link:** [Click here to open on YouTube]({video_link})")