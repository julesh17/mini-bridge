import streamlit as st
from icalendar import Calendar
import re
import io

st.set_page_config(page_title="Export ICS par enseignant")

@st.cache_data
def parse_calendar(file_bytes):
    """
    Retourne (calendar_object, events_list, enseignants_sorted)
    events_list : list de dict { 'component': VEVENT, 'teachers': [ "NOM, Prénom", ... ] }
    """
    cal = Calendar.from_ical(file_bytes)
    events = []
    enseignants_set = set()

    # regex pour capturer "NOM, Prénom" ; accepte la virgule échappée "\," aussi
    teacher_regex = re.compile(
        r'([A-ZÀ-Ÿ][A-ZÀ-Ÿ\'\-\s]+)\\?,\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\'\-\s]+)',
        re.UNICODE
    )

    for component in cal.walk():
        if component.name == "VEVENT":
            desc = component.get("DESCRIPTION")
            # robustification : extraire le texte correctement selon le type renvoyé
            if desc is None:
                desc_text = ""
            elif hasattr(desc, "to_ical"):
                desc_text = desc.to_ical().decode("utf-8")
            else:
                desc_text = str(desc)
            # unescape de la virgule si présente
            desc_text = desc_text.replace("\\,", ",")
            found = teacher_regex.findall(desc_text)
            teachers = []
            for last, first in found:
                name = f"{last.strip()}, {first.strip()}"
                teachers.append(name)
                enseignants_set.add(name)
            events.append({"component": component, "teachers": teachers})
    return cal, events, sorted(enseignants_set)

def build_filtered_calendar(orig_cal, events, selected_teachers):
    new_cal = Calendar()
    # copier les propriétés top-level (VERSION, PRODID, ...)
    for k, v in orig_cal.items():
        new_cal.add(k, v)
    # ajouter uniquement les événements contenant au moins un des enseignants sélectionnés
    for ev in events:
        if any(t in ev["teachers"] for t in selected_teachers):
            new_cal.add_component(ev["component"])
    return new_cal

st.title("Mini-bridge - 📅 Exporter un .ics par enseignant")

uploaded = st.file_uploader("Chargez votre fichier .ics", type=["ics"])
if uploaded:
    cal, events, enseignants = parse_calendar(uploaded.read())
    if not enseignants:
        st.warning(
            "Aucun enseignant détecté. Vérifie le format : les enseignants doivent être au format `NOM, Prénom` dans le champ DESCRIPTION."
        )
    else:
        st.info(f"{len(enseignants)} enseignant(s) détecté(s).")
        selected = st.multiselect("Sélectionnez un ou plusieurs enseignant(s) :", enseignants)

        if selected:
            # construire une liste d'événements correspondants pour prévisualisation
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
                        "ENSEIGNANTS (extraits)": ", ".join(ev["teachers"]) or ""
                    })

            st.write(f"Événements correspondant aux enseignants sélectionnés : **{len(matching)}**")
            if matching:
                st.table(matching)

            new_cal = build_filtered_calendar(cal, events, selected)
            ics_bytes = new_cal.to_ical()
            fname = "_".join([s.replace(" ", "_") for s in selected]) + ".ics"
            st.download_button(
                label="Télécharger le .ics filtré",
                data=ics_bytes,
                file_name=fname,
                mime="text/calendar"
            )
        else:
            st.info("Sélectionne au moins un enseignant pour générer le fichier .ics.")
