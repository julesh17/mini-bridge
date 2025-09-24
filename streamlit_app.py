import streamlit as st
from icalendar import Calendar, Event
import io

# Charger le fichier ICS
@st.cache_data
def load_calendar(file):
    gcal = Calendar.from_ical(file.read())
    events = []
    enseignants = set()
    for component in gcal.walk():
        if component.name == "VEVENT":
            desc = component.get("DESCRIPTION", "")
            if "Enseignant(s):" in desc:
                # Extraire les enseignants
                for part in desc.split("Enseignant(s):")[-1].split("\\n")[0].split(","):
                    enseignants.add(part.strip())
            events.append(component)
    return gcal, events, sorted(enseignants)

def filter_calendar(gcal, events, enseignant):
    new_cal = Calendar()
    # Copier les propriétés principales
    for name, value in gcal.items():
        new_cal.add(name, value)

    for component in events:
        desc = component.get("DESCRIPTION", "")
        if enseignant in desc:
            new_cal.add_component(component)
    return new_cal

st.title("📅 Mini-bridge : Export d’emplois du temps par enseignant")

uploaded_file = st.file_uploader("Chargez un fichier .ics", type=["ics"])

if uploaded_file:
    gcal, events, enseignants = load_calendar(uploaded_file)

    selected = st.selectbox("Choisissez un enseignant :", enseignants)

    if selected:
        new_cal = filter_calendar(gcal, events, selected)
        output = io.BytesIO(new_cal.to_ical())
        st.download_button(
            label=f"Télécharger le calendrier de {selected}",
            data=output,
            file_name=f"{selected.replace(' ', '_')}.ics",
            mime="text/calendar"
        )
