import streamlit as st
import os 
from dotenv import load_dotenv
import pickle
import requests
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
OMDB_KEY = os.getenv("OMDB_KEY")

if not OMDB_KEY:
    OMDB_KEY = st.secrets["OMDB_KEY"]

st.set_page_config(page_title="Movie Recommender", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
.block-container {padding-top: 1rem;}
.hero {
    position: relative; overflow: hidden; min-height: 400px;
    border-radius: 18px; padding: 40px 60px; margin-bottom: 25px;
    display: flex; justify-content: space-between; align-items: center;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
}
.hero-bg {position: absolute; inset: 0; background-size: cover; background-position: center;}
.hero-bg.blur {filter: blur(30px) brightness(0.45); transform: scale(1.2);}
.hero-text {position: relative; z-index: 1;}
.hero h1 {
    display: inline-block; color: white; background: rgba(0,0,0,0.45);
    padding: 6px 18px; border-radius: 10px; font-family: monospace; margin: 0 0 10px 0;
}
.hero p {
    display: inline-block; color: white; background: rgba(0,0,0,0.45);
    padding: 4px 14px; border-radius: 10px; font-family: monospace; font-size: 14px;
}
.hero-poster {
    position: relative; z-index: 1; height: 340px; border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.7);
}
.row-title {
    display: inline-block; background: white; color: #111; padding: 6px 16px;
    border-radius: 20px; font-family: monospace; font-size: 14px; margin-bottom: 12px;
}
.row {display: grid; grid-template-columns: repeat(6, 1fr); gap: 20px;}
.card {text-align: center; min-width: 0;}
.card img {
    width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4); transition: transform 0.2s;
}
.card img:hover {transform: scale(1.04);}
.card span {
    display: block; font-size: 13px; margin-top: 8px; color: #888;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.noposter {
    width: 100%; aspect-ratio: 2/3; border-radius: 10px; padding: 10px;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #1e3c72, #2a5298);
    color: white; font-weight: bold; font-size: 14px; box-sizing: border-box;
}
.auth-title {
    display: inline-block; background: white; color: #111; padding: 6px 16px;
    border-radius: 20px; font-family: monospace; font-size: 14px; margin: 30px 0 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ---------- Data load ----------
@st.cache_resource
def load_data():
    df = pickle.load(open("movies.pkl", "rb"))
    sim = pickle.load(open("similarity.pkl", "rb"))
    return df, sim

df, similarity = load_data()

@st.cache_data(show_spinner=False)
def fetch_poster(title):
    try:
        r = requests.get(
            "https://www.omdbapi.com/",
            params={"apikey": OMDB_KEY, "t": title},
            timeout=5,
        )
        poster = r.json().get("Poster")
        if poster and poster != "N/A":
            return poster
    except Exception:
        pass
    return None

def resize(url, size):
    return url.replace("SX300", f"SX{size}") if url else None

def recommend(title, n=11):
    idx = df[df["title"] == title].index[0]
    scores = sorted(enumerate(similarity[idx]), key=lambda x: x[1], reverse=True)[1:n + 1]
    titles = [title] + [df.iloc[i]["title"] for i, _ in scores]
    with ThreadPoolExecutor(max_workers=8) as ex:
        posters = list(ex.map(fetch_poster, titles))
    return titles, posters

def show_row(title_text, titles, posters):
    st.markdown(f'<div class="row-title">{title_text}</div>', unsafe_allow_html=True)
    cards = ""
    for t, p in zip(titles, posters):
        if p:
            cards += f'<div class="card"><img src="{resize(p, 600)}"><span>{t}</span></div>'
        else:
            cards += f'<div class="card"><div class="noposter">{t}</div><span>{t}</span></div>'
    st.markdown(f'<div class="row">{cards}</div>', unsafe_allow_html=True)

# ---------- Hero ----------
hero_box = st.empty()

def render_hero(poster):
    text = ('<div class="hero-text"><h1>Welcome.</h1><br>'
            '<p>Search here to get AI based movies Recommendation !</p></div>')
    if poster:
        big = resize(poster, 900)
        html = (f'<div class="hero"><div class="hero-bg blur" style="background-image:url(\'{big}\')"></div>'
                f'{text}<img class="hero-poster" src="{big}"></div>')
    else:
        html = f'<div class="hero">{text}</div>'
    hero_box.markdown(html, unsafe_allow_html=True)

# ---------- Search ----------
query = st.text_input("Search", placeholder="Search movies...", label_visibility="collapsed")

all_titles = df["title"].tolist()
selected = None

if query.strip():
    matches = [t for t in all_titles if query.lower() in t.lower()]
    if matches:
        selected = st.selectbox("Matching movies", matches[:50]) if len(matches) > 1 else matches[0]
    else:
        st.warning("Movie not found. Please check the spelling.")
else:
    selected = "Pirates of the Caribbean: At World's End"
    if selected not in all_titles:
        selected = all_titles[0]

# ---------- Hero + Recommendations ----------
if selected:
    render_hero(fetch_poster(selected))
    with st.spinner("Loading recommendations..."):
        titles, posters = recommend(selected, n=11)
    show_row(f"For you: because you watched {selected}", titles, posters)
else:
    render_hero(None)

