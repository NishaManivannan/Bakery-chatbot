from flask import Flask, render_template, request, jsonify, session
import os, time, difflib, uuid, re
from gtts import gTTS
from db import create_table, insert_order, delete_order_by_name_phone, order_exists

app = Flask(__name__)
app.secret_key = os.urandom(24)

AUDIO_DIR = os.path.join("static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

SESSION_TIMEOUT = 300
create_table()

PRICES = {
    "cake": {
        "Chocolate": {"Cherries": 350, "Nuts": 360, "Extra Frosting": 370},
        "Vanilla": {"Cherries": 340, "Nuts": 350, "Extra Frosting": 360},
        "Strawberry": {"Cherries": 345, "Nuts": 355, "Extra Frosting": 365}
    },
    "cookies": {
        "Chocolate Chip": 150,
        "Oatmeal Raisin": 140,
        "Sugar": 130
    },
    "pizza": {
        "Small": {"Margherita": 200, "Pepperoni": 250},
        "Medium": {"Margherita": 300, "Pepperoni": 350},
        "Large": {"Margherita": 400, "Pepperoni": 450}
    },
    "customization": 30
}

NUM_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"
}

def reset_session():
    session.clear()
    session['stage'] = 'welcome'
    session['last_active'] = time.time()

def cleanup_audio_files():
    now = time.time()
    for fn in os.listdir(AUDIO_DIR):
        path = os.path.join(AUDIO_DIR, fn)
        if now - os.path.getmtime(path) > 3600:
            os.remove(path)

def speak_response(text):
    if not text.strip():
        return None
    filename = f"response_{uuid.uuid4().hex}.mp3"
    path = os.path.join(AUDIO_DIR, filename)
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(path)
    return f"/static/audio/{filename}"

def generate_audio(text):
    path = speak_response(text)
    cleanup_audio_files()
    return path

def clean_phone_input(raw):
    raw = re.sub(r'[.\-(),]', '', raw)
    words = raw.strip().lower().split()
    if all(word in NUM_WORDS for word in words):
        digits = ''.join(NUM_WORDS[word] for word in words)
        return digits
    return re.sub(r'\D', '', raw)

def fuzzy_match(user_input, options):
    user_input = user_input.lower()
    for opt in options:
        if opt.lower() in user_input:
            return opt
    match = difflib.get_close_matches(user_input, [o.lower() for o in options], n=1, cutoff=0.4)
    return options[[o.lower() for o in options].index(match[0])] if match else None

def extract_name(msg):
    patterns = [r"i am (.+)", r"i'm (.+)", r"my name is (.+)"]
    for pat in patterns:
        match = re.search(pat, msg, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return msg.strip().title()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/reset", methods=["POST"])
def reset():
    reset_session()
    return ("", 204)

@app.route("/get", methods=["POST"])
def chat():
    msg = request.form.get("msg", "").strip()
    voice = request.form.get("voice", "false") == "true"
    now = time.time()

    if 'last_active' in session and now - session['last_active'] > SESSION_TIMEOUT:
        reset_session()
    session['last_active'] = now
    stage = session.get("stage", "welcome")

    if "home" in msg.lower():
        reset_session()
        text = "Starting fresh. Welcome back to Bake Talks.\nWould you like to query, place, or cancel an order?"
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    if stage == "welcome":
        session['stage'] = "get_action"
        text = "Welcome to Bake Talks.\nWould you like to query, place, or cancel an order?"
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "get_action":
        choice = fuzzy_match(msg, ["Query", "Place", "Cancel"])
        if choice == "Query":
            response = "Here is our full pricing list:\n"
            for cat, items in PRICES.items():
                if cat == "customization":
                    response += f"\nCustomization charge: ₹{items} extra\n"
                    continue
                response += f"\n{cat.title()}:\n"
                for k, v in items.items():
                    if isinstance(v, dict):
                        response += f"  {k}:\n"
                        for subk, subv in v.items():
                            response += f"    - {subk}: ₹{subv}\n"
                    else:
                        response += f"  - {k}: ₹{v}\n"
            response += "\nType 'home' to start over or 'place' to begin ordering."
            audio_url = generate_audio(response) if voice else None
            return jsonify(response=response, audio_url=audio_url)
        elif choice == "Place":
            session['stage'] = "get_name"
            text = "Let's get started.\nWhat is your name?"
        elif choice == "Cancel":
            session['stage'] = "cancel_name"
            text = "To cancel your order, please enter your name."
        else:
            text = "Please type query, place, or cancel to continue."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "cancel_name":
        session['cancel_name'] = extract_name(msg)
        session['stage'] = "cancel_phone"
        text = "Please enter your 10-digit phone number for cancellation."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "cancel_phone":
        phone = clean_phone_input(msg)
        name = session.get("cancel_name")
        if phone.isdigit() and len(phone) == 10:
            if order_exists(name, phone):
                delete_order_by_name_phone(name, phone)
                text = "Your order has been cancelled successfully."
            else:
                text = "No matching order found with the provided name and phone."
            reset_session()
        else:
            text = "Invalid phone number. Please enter a valid 10-digit phone number."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "get_name":
        session['name'] = extract_name(msg)
        session['stage'] = "get_phone"
        text = f"Thanks, {session['name']}. Could you share your 10-digit phone number?"
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "get_phone":
        phone = clean_phone_input(msg)
        if phone.isdigit() and len(phone) == 10:
            session['phone'] = phone
            session['stage'] = "category"
            text = "Great. Please choose a category: Cake, Cookies, or Pizza."
        else:
            text = "That doesn't look right. Please enter a valid 10-digit phone number."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "category":
        choice = fuzzy_match(msg, ["Cake", "Cookies", "Pizza"])
        if not choice:
            text = "Please choose from Cake, Cookies, or Pizza."
        else:
            session['category'] = choice
            session['stage'] = "flavor"
            if choice == "Cake":
                text = "Choose a cake flavor: Chocolate, Vanilla, or Strawberry."
            elif choice == "Cookies":
                text = "Choose a cookie type: Chocolate Chip, Oatmeal Raisin, or Sugar."
            elif choice == "Pizza":
                text = "What size would you like? Small, Medium, or Large."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "flavor":
        category = session.get("category")
        if category == "Cake":
            choice = fuzzy_match(msg, ["Chocolate", "Vanilla", "Strawberry"])
            if not choice:
                text = "Choose from: Chocolate, Vanilla, or Strawberry."
            else:
                session['flavor'] = choice
                session['stage'] = "topping"
                text = f"Nice choice. What topping for your {choice} cake? Cherries, Nuts, or Extra Frosting?"
        elif category == "Cookies":
            choice = fuzzy_match(msg, ["Chocolate Chip", "Oatmeal Raisin", "Sugar"])
            if not choice:
                text = "Please choose from Chocolate Chip, Oatmeal Raisin, or Sugar."
            else:
                session['flavor'] = choice
                session['stage'] = "confirm"
                text = f"You chose {choice} cookies. Ready to confirm? Type yes to confirm or no to cancel."
        elif category == "Pizza":
            choice = fuzzy_match(msg, ["Small", "Medium", "Large"])
            if not choice:
                text = "Please choose a size: Small, Medium, or Large."
            else:
                session['size'] = choice
                session['stage'] = "topping"
                text = f"{choice} pizza selected. Now pick a flavor: Margherita or Pepperoni."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "topping":
        category = session.get("category")
        if category == "Cake":
            choice = fuzzy_match(msg, ["Cherries", "Nuts", "Extra Frosting"])
            if not choice:
                text = "Pick a topping: Cherries, Nuts, or Extra Frosting."
            else:
                session['topping'] = choice
                session['stage'] = "customize"
                text = f"{choice} topping added. Want a custom message on your cake? Type it, or say 'no'."
        elif category == "Pizza":
            choice = fuzzy_match(msg, ["Margherita", "Pepperoni"])
            if not choice:
                text = "Choose between Margherita and Pepperoni."
            else:
                session['flavor'] = choice
                session['stage'] = "customize"
                text = f"{choice} pizza selected. Any special instructions or extra toppings? Type it, or 'no' to skip."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "customize":
        session['custom'] = msg if msg.lower() != 'no' else None
        session['stage'] = "confirm"
        text = "Almost done. Ready to place the order?\nType yes to confirm or no to cancel."
        audio_url = generate_audio(text) if voice else None
        return jsonify(response=text, audio_url=audio_url)

    elif stage == "confirm":
        confirm_keywords = ["yes", "y", "confirm", "ok", "okay", "sure", "yes proceed", "go ahead", "yeah"]
        match = fuzzy_match(msg, confirm_keywords)
        if match:
            name = session.get('name')
            phone = session.get('phone')
            cat = session.get('category')
            flavor = session.get('flavor', '')
            topping = session.get('topping', '')
            size = session.get('size', '')
            custom = session.get('custom')

            if cat == "Cake":
                base_price = PRICES["cake"][flavor][topping]
            elif cat == "Cookies":
                base_price = PRICES["cookies"][flavor]
            elif cat == "Pizza":
                base_price = PRICES["pizza"][size][flavor]
            else:
                base_price = 0

            final_price = base_price + (PRICES["customization"] if custom else 0)
            insert_order(name, phone, cat, flavor, topping, size, custom, final_price)

            summary = f"Thank you {name}. Your order for "
            if cat == "Cake":
                summary += f"a {flavor} cake with {topping}"
            elif cat == "Cookies":
                summary += f"{flavor} cookies"
            elif cat == "Pizza":
                summary += f"a {size} {flavor} pizza"
            if custom:
                summary += f" and customization '{custom}'"
            summary += f" has been placed successfully.\nTotal cost: ₹{final_price}.\nType home to start a new order."
        else:
            reset_session()
            summary = "Order cancelled. You can start again anytime by typing hi."

        audio_url = generate_audio(summary) if voice else None
        return jsonify(response=summary, audio_url=audio_url)

    fallback = "I didn’t quite get that. Please try again or type home to restart."
    audio_url = generate_audio(fallback) if voice else None
    return jsonify(response=fallback, audio_url=audio_url)

if __name__ == "__main__":
    app.run(debug=True)
