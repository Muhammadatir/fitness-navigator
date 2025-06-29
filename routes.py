import logging
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from FitnessNavigator.utils import generate_workout_plan, generate_diet_plan, calculate_bmi
from FitnessNavigator.app import app
import google.generativeai as genai
import os

# Configure Gemini API
genai.configure(api_key=app.config['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash-latest')

@app.route('/')
def index():
    return render_template('index.html', enable_chat=True)

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    # Log the contact submission
    logging.debug(f"Contact form submission - Name: {name}, Email: {email}, Message: {message}")

    flash('Thank you for your message! We will get back to you soon.', 'success')
    return redirect(url_for('index'))

@app.route('/generate_plan', methods=['POST'])
def generate_plan():
    try:
        def safe_int(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0
        def safe_float(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0
        def safe_str(val):
            return str(val) if val is not None else ''

        user_data = {
            'age': safe_int(request.form.get('age', 0)),
            'gender': safe_str(request.form.get('gender', '')),
            'height': safe_float(request.form.get('height', 0.0)),
            'weight': safe_float(request.form.get('weight', 0.0)),
            'food_preference': safe_str(request.form.get('food_preference', '')),
            'intensity': safe_str(request.form.get('intensity', ''))
        }

        # Remove any keys with empty string or zero values if you want to enforce required fields
        for k, v in user_data.items():
            if v in [None, '', 0, 0.0]:
                flash('Please fill in all required fields.', 'warning')
                return redirect(url_for('index'))

        # Calculate BMI
        bmi, bmi_category = calculate_bmi(user_data['height'], user_data['weight'])
        user_data['bmi'] = bmi
        user_data['bmi_category'] = bmi_category

        # Generate plans
        diet_plan = generate_diet_plan(user_data['gender'], user_data['food_preference'], bmi_category)
        workout_plan = generate_workout_plan(user_data['gender'], user_data['intensity'])

        # Store in session
        session['user_data'] = user_data
        session['diet_plan'] = diet_plan
        session['workout_plan'] = workout_plan

        return redirect(url_for('diet_plan'))
    except Exception as e:
        logging.error("Error generating plan: %s", e, exc_info=True)
        flash('An error occurred while generating your plans. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/diet_plan')
def diet_plan():
    if 'user_data' not in session or 'diet_plan' not in session:
        flash('Please fill out the form first to generate your diet plan.', 'warning')
        return redirect(url_for('index'))

    return render_template(
        'diet_plan.html',
        user_data=session['user_data'],
        diet_plan=session['diet_plan']
    )

@app.route('/workout_plan')
def workout_plan():
    if 'user_data' not in session or 'workout_plan' not in session:
        flash('Please fill out the form first to generate your workout plan.', 'warning')
        return redirect(url_for('index'))

    return render_template(
        'workout_plan.html',
        user_data=session['user_data'],
        workout_plan=session['workout_plan']
    )

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message', '')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Generate response using Gemini
        response = model.generate_content(user_message)
        
        return jsonify({
            'response': response.text
        })
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your message'}), 500

if __name__ == "__main__":
    app.run(debug=True)
