CartEngine
A production-ready Django e-commerce backend featuring secure atomic transactions, row-level stock locking, Paystack payment processing, webhook verification, and Sentry error monitoring.
 
Key Features

- Secure User Authentication: Built-in Django authentication supporting user signup, secure sessions, and login-required decorators.
- Dynamic Shopping Cart: Full cart management allowing users to add products, update quantities dynamically, or remove items seamlessly.
- Concurrent Stock Management: USes database-level row locking (`select_for_update`) wrapped in atomic transactions (transaction.atomic()`) to prevent race conditions and overselling during high-traffic checkouts.
- Paystack Payment Integration: Initializes checkout sessions, verifies transaction statuses, and handles cryptographically signed webhooks (`hmac` + `sha512`) to confirm payments securely.
- Production Error Tracking: Integrated with Sentry SDK to capture and monitor exceptions in real-time.

Tech Stack

- Backend: Python, Django
- Database: SQLite (Development) / MySQL or PostgreSQL (Production ready)
- Payment Gateway: Paystack API
- Monitoring: Sentry SDK
- Styling: Tailwind CSS
- Installation & Setup Locally

1. Clone the repository:
   Bash
   git clone [https://github.com/YourUsername/CartEngine.git](https://github.com/YourUsername/CartEngine.git)
   cd CartEngine

   Create and activate a virtual environment:
Create and activate a virtual environment
Bash
python -m venv venv
On Windows:
- venv\Scripts\activate
On macOS/Linux:
- source venv/bin/activate

  
Install dependencies:
Bash
- pip install -r requirements.txt

  
Set up environment variables:
Create a .env file in the root directory and add your credentials:

Code snippet
SECRET_KEY=your_django_secret_key
DEBUG=True
PAYSTACK_SECRET_KEY=your_paystack_secret_key
SENTRY_DSN=your_sentry_dsn
Run database migrations:

Bash
- python manage.py makemigrations
- python manage.py migrate
Start the development server:

Bash
python manage.py runserver

API & Webhook Endpoints
- Checkout Route: POST /orders/checkout/ — Initializes cart items, locks stock rows safely, and redirects to Paystack.

- Payment Verification: GET /orders/success/<order_id>/ — Verifies transaction status directly with Paystack's server.

- Webhook Listener: POST /orders/webhook/ — Securely listens for asynchronous charge.success events from Paystack with signature validation.

Security Highlights
- Webhook Signature Verification: Every incoming webhook request from Paystack is validated using HMAC-SHA512 hashing to prevent unauthorized spoofing.

- Environment Isolation: Sensitive credentials are completely decoupled from source control using environment variables.

