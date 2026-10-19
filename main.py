"""TOKYO web app (Streamlit). Run: streamlit run main.py"""
import hmac

import streamlit as st
from streamlit_folium import st_folium

import config
from core import assistant, context
from services.calendar_svc import add_deadline, get_deadlines_list
from services.map_svc import get_madrid_map

st.set_page_config(page_title="TOKYO", page_icon="⚡", layout="wide")

# --- LOGIN: the app can read/write your calendar, so never leave it open ---
if config.WEB_PASSWORD and not st.session_state.get("auth"):
  pw = st.text_input("Password", type="password")
  if pw and hmac.compare_digest(pw, config.WEB_PASSWORD):
    st.session_state.auth = True
    st.rerun()
  st.stop()

ss = st.session_state
ss.setdefault("messages", [{"role": "assistant",
                            "content": "Halo! TOKYO online. Ada yang bisa kubantu hari ini?"}])
ss.setdefault("lang", config.DEFAULT_LANG)
ss.setdefault("mic_key", 0)
ss.setdefault("speak_text", True)

st.title("⚡ TOKYO")
st.caption("Tracks Obligations, Keeps You On-time")

# --- SIDEBAR ---
with st.sidebar:
  w = context.weather()
  if w:
    st.metric("Madrid", f"{w['temperature']}°C", f"terasa {w['feels_like']}°C",
              delta_color="off")
    st.caption(f"{w['condition']} · {w['min']}–{w['max']}°C · hujan {w['rain_chance']}%")

  st.divider()
  st.subheader("📅 Agenda")
  events = context.events()
  st.markdown(get_deadlines_list(events) if events is not None
              else "⚠️ Google Calendar belum terhubung.")

  with st.expander("➕ Tambah agenda"):
    title = st.text_input("Judul")
    date = st.date_input("Tanggal")
    if st.button("Simpan agenda") and title:
      st.success(add_deadline(title, str(date)))
      context.invalidate("agenda")
      st.rerun()

  st.divider()
  ss.speak_text = st.toggle("🔊 Jawab dengan suara", value=ss.speak_text)
  if st.button("🧹 Hapus percakapan"):
    ss.messages = ss.messages[:1]
    st.rerun()

  with st.expander("🗺️ Peta Madrid"):
    place = st.text_input("Cari lokasi", "Gran Via")
    if place:
      st_folium(get_madrid_map(place), height=220, width=280)

# --- CHAT HISTORY ---
for i, m in enumerate(ss.messages):
  with st.chat_message(m["role"]):
    st.markdown(m["content"])
    if m.get("audio"):
      # Autoplay only the newest reply, once.
      st.audio(m["audio"], format="audio/wav", autoplay=m.pop("autoplay", False))


def history() -> list:
  return [{"role": m["role"], "content": m["content"]} for m in ss.messages[1:]]


def respond(reply: assistant.Reply, user_text: str, voice_in: bool) -> None:
  ss.lang = reply.lang
  ss.messages.append({"role": "user", "content": ("🎙️ " if voice_in else "") + user_text})
  msg = {"role": "assistant", "content": reply.text}
  if voice_in or ss.speak_text:
    msg["audio"], msg["autoplay"] = assistant.speak(reply), True
  for old in ss.messages:  # keep audio only on the latest reply to save memory
    old.pop("audio", None)
  ss.messages.append(msg)


# --- INPUTS ---
# Changing the widget key after use resets the recorder, so one recording
# is processed exactly once even though Streamlit reruns the script.
audio = st.audio_input("Bicara ke TOKYO", key=f"mic_{ss.mic_key}")
if audio:
  with st.spinner("Mendengarkan & berpikir..."):
    reply = assistant.ask_voice(audio.getvalue(), history(), ss.lang)
  respond(reply, reply.heard or "(tidak terdengar)", voice_in=True)
  ss.mic_key += 1
  st.rerun()

if prompt := st.chat_input("Ketik pesan untuk TOKYO..."):
  with st.spinner("TOKYO sedang berpikir..."):
    reply = assistant.ask_text(prompt, history(), ss.lang)
  respond(reply, prompt, voice_in=False)
  st.rerun()
