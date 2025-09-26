import streamlit as st
from icalendar import Calendar, Event, Timezone, TimezoneStandard, TimezoneDaylight
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Export ICS par enseignant (multi-fichiers + groupes/promo/classe)")

def detect_file_context(filename):
    """
    Analyse le nom du fichier pour extraire promo (P1/P2) et classe (A1..A6).
    Retourne dict { 'promo': 'P1', 'classe': 'A3' }
    """
    promo_regex = re.compile(r'\bP[1-9]\b', re.IGNORECASE)
    classe_regex = re.compile(r'\bA[1-9]\b', re.IGNORECASE)

    promo = None
    classe = None

    promo_match = promo_regex.findall(filename)
    if promo_match:
        promo = promo_match[0].upper()

    classe_match = classe_regex.findall(filename)
    if classe_match:
        classe = classe_match[0].upper()

    return {"promo": promo, "classe": classe}

def parse_calendars(files):
    all_cals = []
    events = []
    enseignants_set = set()

    teacher_regex = re.compile(
        r'([A-ZÀ-Ÿ][A-ZÀ-Ÿ\'\-\s]+)\\?,\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\'\-\s]+)',
        re.UNICODE
    )
    group_regex = re.compile(r'G\s*([1-9])', re.IGNORECASE)

    for f in files:
        context = detect_file_context(f.name)
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

                # Détection enseignants
                found = teacher_regex.findall(desc_text)
                teachers = []
                for last, first in found:
                    name = f"{last.strip()}, {first.strip()}"
                    teachers.append(name)
                    enseignants_set.add(name)

                # Détection groupes
                groups = group_regex.findall(desc_text)
                groups_fmt = [f"G{g}" for g in groups]

                events.append({
                    "component": component,
                    "teachers": teachers,
                    "groups": groups_fmt,
                    "promo": context["promo"],
                    "classe": context["classe"]
                })
    return all_cals, events, sorted(enseignants_set)

def build_paris_vtimezone():
    """Construit le bloc VTIMEZONE pour Europe/Paris (CET/CEST)."""
    tz = Timezone()
    tz.add("TZID", "Europe/Paris")
    tz.add("X-LIC-LOCATION", "Europe/Paris")

    # Heure d’hiver (CET)
    standard = TimezoneStandard()
    standard.add("TZOFFSETFROM", timedelta(hours=2))
    standard.add("TZOFFSETTO", timedelta(hours=1))
    standard.add("TZNAME", "CET")
    standard.add("DTSTART", datetime(1970, 10, 25, 3, 0, 0))
    standard.add("RRULE", {"FREQ": "YEARLY", "BYMONTH": 10, "BYDAY": "-1SU"})
    tz.add_component(standard)

    # Heure d’été (CEST)
    daylight = TimezoneDaylight()
    daylight.add("TZOFFSETFROM", timedelta(hours=1))
    daylight.add("TZOFFSETTO", timedelta(hours=2))
    daylight.add("TZNAME", "CEST")
    daylight.add("DTSTART", datetime(1970, 3, 29, 2, 0, 0))
    daylight.add("RRULE", {"FREQ": "YEARLY", "BYMONTH": 3, "BYDAY": "-1SU"})
    tz.add_component(daylight)

    return tz

def build_filtered_calendar(orig_cals, events, selected_teachers):
    new_cal = Calendar()
    if orig_cals:
        for k, v in orig_cals[0].items():
            new_cal.add(k, v)

    # 🔹 Ajouter définition Europe/Paris
    new_cal.add_component(build_paris_vtimezone())

    for ev in events:
        if any(t in ev["teachers"] for t in selected_teachers):
            comp = ev["component"]
            summary = str(comp.get("SUMMARY") or "")

            extra_parts = []
            if ev["promo"]:
                extra_parts.append(ev["promo"])
            if ev["classe"]:
                extra_parts.append(ev["classe"])
            if ev["groups"]:
                extra_parts.extend(ev["groups"])

            if extra_parts:
                summary = f"{summary} [{' - '.join(extra_parts)}]"

            # cloner l’événement
            new_event = Event()
            for k, v in comp.items():
                if k.upper() == "SUMMARY":
                    new_event.add("SUMMARY", summary)
                else:
                    new_event.add(k, v)
            for sub in comp.subcomponents:
                new_event.add_component(sub)

            new_cal.add_component(new_event)

    return new_cal

st.title("📅 Mini-bridge : Exporter un .ics par enseignant")

uploaded_files = st.file_uploader(
    "Chargez un ou plusieurs fichiers .ics", 
    type=["ics"], 
    accept_multiple_files=True
)

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
                    extra = []
                    if ev["promo"]: extra.append(ev["promo"])
                    if ev["classe"]: extra.append(ev["classe"])
                    if ev["groups"]: extra.extend(ev["groups"])
                    if extra:
                        summary = f"{summary} [{' - '.join(extra)}]"
                    matching.append({
                        "DTSTART": start,
                        "DTEND": end,
                        "SUMMARY (modifié)": summary,
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
