# MedBot: Global Post-Op Care

Patients leaving the hospital often cannot read their discharge papers, either because the handwriting is hard
to read or because the instructions are in a language they do not speak. MedBot turns a photo of a discharge
paper into simple, spoken instructions in the patient's own language.

## How it works

**Google Gemini API**
- Vision reads the photographed (often handwritten) discharge paper and extracts medicines, doses, timing,
  wound care and warning signs as structured JSON.
- It never guesses unreadable text. Anything unclear is flagged and the patient is told to ask a doctor or
  pharmacist.
- A second call simplifies the instructions to a chosen reading level and translates them, including the
  whole interface.
- A third call checks the translation back against the original extraction.
- Gemini answers the patient's spoken questions using only the document.

**ElevenLabs**
- Text-to-speech reads the instructions aloud in the patient's language (full audio, per-medicine clips, and
  a downloadable MP3 for sharing on WhatsApp).
- Speech-to-text (Scribe) lets the patient ask questions by voice.

A person confirms the time of day for each medicine before the final instructions are produced, because it is
often not written on the paper.

## Run it

1. Install Python 3.10 or newer.
2. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a file named `.streamlit/secrets.toml` with your own keys. Do not commit this file.

   ```toml
   GEMINI_KEY = "your-gemini-api-key"
   ELEVEN_KEY = "sk_your-elevenlabs-api-key"
   ```

4. Start the app:

   ```
   streamlit run app.py
   ```

## Notes

- MedBot is an aid, not a medical device. Patients must always confirm medicines and doses with their doctor
  or pharmacist.
- The ElevenLabs model is set by `TTS_MODEL` at the top of `app.py`.