import streamlit as st
from icalendar import Calendar
import re
import io

st.set_page_config(page_title="Export ICS par enseignant (multi-fichiers)")

@st.cache_data
def parse_calendars(files):
    """
    Prend une liste de fichiers .ics et retourne :
      - liste des Calendar complets
      - liste des events [{ 'component': VEVENT, 'teachers': [...] }]
      - liste des enseignants uniques triés
    """
    all_cals = []
    events = []
    enseignants_set = set()

    teacher_regex = re.compile(
        r'([A-ZÀ-Ÿ][A-ZÀ-Ÿ\'\-\s]+)\\?,\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\'\-\s]+)',
        re.UNICODE
    )

    for f in files:
        cal = Calendar.from_ical(f.read())
        all_cals.append(cal)
        for component in cal.walk():
            if component.name == "VEVENT":
                desc = component.get("DESCRIPTION")
                if desc is None:
                    desc_text = ""
                elif hasattr(desc, "to_ical"):
                    desc_text = desc.to_ical().decode("utf-8")
                else:
                    desc_text = str(desc)

                desc_text = desc_text.replace("\\,", ",")
                found = teacher_regex.findall(desc_text)
                teachers = []
                for last, first in found:
                    name = f"{last.strip()}, {first.strip()}"
                    teachers.append(name)
                    enseignants_set.add(name)

                events.append({"component": component, "teachers": teachers})

    return all_cals, events, sorted(enseignants_set)

def build_filtered_calendar(orig_cals, events, selected_teachers):
    new_cal = Calendar()
    # Copier les propriétés du premier calendrier (VERSION, PRODID, etc.)
    if orig_cals:
        for k, v in orig_cals[0].items():
            new_cal.add(k, v)
    # Ajouter uniquement les événements correspondant
    for ev in events:
        if any(t in ev["teachers"] for t in selected_teachers):
            new_cal.add_component(ev["component"])
    return new_cal

st.title("📅 Mini-bridge : Exporter un .ics par enseignant")

uploaded_files = st.file_uploader("Chargez un ou plusieurs fichiers .ics (EDT)", type=["ics"], accept_multiple_files=True)

if uploaded_files:
    all_cals, events, enseignants = parse_calendars(uploaded_files)

    if not enseignants:
        st.warning("Aucun enseignant détecté dans les fichiers.")
    else:
        st.info(f"{len(enseignants)} enseignant(s) détecté(s) dans {len(uploaded_files)} fichier(s).")

        selected = st.multiselect("Sélectionnez un ou plusieurs enseignant(s) :", enseignants)

        if selected:
            matching = []
            for ev in events:
                if any(t in ev["teachers"] for t in selected):
                    comp = ev["component"]
                    start = comp.get("DTSTART").dt if comp.get("DTSTART") else None
                    end = comp.get("DTEND").dt if comp.get("DTEND") else None
                    summary = str(comp.get("SUMMARY") or "")
                    matching.append({
                        "DTSTART": start,
                        "DTEND": end,
                        "SUMMARY": summary,
                        "ENSEIGNANTS": ", ".join(ev["teachers"]) or ""
                    })

            st.write(f"Événements correspondant aux enseignants sélectionnés : **{len(matching)}**")
            if matching:
                st.table(matching)

            new_cal = build_filtered_calendar(all_cals, events, selected)
            ics_bytes = new_cal.to_ical()
            fname = "_".join([s.replace(' ', '_') for s in selected]) + ".ics"
            st.download_button(
                label="Télécharger le .ics filtré",
                data=ics_bytes,
                file_name=fname,
                mime="text/calendar"
            )
        else:
            st.info("Sélectionnez au moins un enseignant.")
