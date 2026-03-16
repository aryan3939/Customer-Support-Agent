"""
Seed the Knowledge Base — populate articles + vector embeddings in Supabase.

WHY THIS SCRIPT EXISTS:
-----------------------
The RAG system needs KB articles stored in the database WITH their vector
embeddings. This script:

1. Inserts all KB articles into the `knowledge_articles` table
2. Chunks each article's content into smaller pieces
3. Generates vector embeddings for each chunk using sentence-transformers
4. Stores chunks + embeddings in the `kb_embeddings` table

RUN THIS ONCE AFTER SETTING UP THE DATABASE:
    python scripts/seed_kb.py

It's safe to re-run — it clears existing data and re-seeds everything.

TIMING:
    - First run: ~30 seconds (downloads the embedding model ~90MB)
    - Subsequent runs: ~5 seconds (model is cached locally)
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text


# =============================================================================
# Knowledge Base Articles — the data to seed
# =============================================================================

KB_ARTICLES = [
    # ---- ACCOUNT ----
    {
        "title": "Password Reset Guide",
        "category": "account",
        "content": (
            "To reset your password: 1) Go to the login page and click 'Forgot Password'. "
            "2) Enter your registered email address. 3) Check your email for a reset link "
            "(check spam folder too). 4) Click the link and set a new password. "
            "5) Password must be at least 8 characters with one number and one special character. "
            "If you don't receive the email within 5 minutes, try again or contact support. "
            "Note: Reset links expire after 24 hours for security."
        ),
    },
    {
        "title": "Two-Factor Authentication (2FA) Setup",
        "category": "account",
        "content": (
            "To enable 2FA: 1) Go to Account Settings → Security → Two-Factor Authentication. "
            "2) Choose your method: Authenticator App (recommended) or SMS. "
            "3) Scan the QR code with Google Authenticator, Authy, or Microsoft Authenticator. "
            "4) Enter the 6-digit verification code to confirm setup. "
            "5) Save the backup recovery codes in a safe place — you'll need these if you lose your phone. "
            "To disable 2FA: Go to Settings → Security → Disable 2FA (requires current password). "
            "If locked out of 2FA, contact support with your backup recovery code."
        ),
    },
    {
        "title": "Account Setup & Profile Configuration",
        "category": "account",
        "content": (
            "To set up your account: 1) Sign up at our website with your email. "
            "2) Verify your email address by clicking the confirmation link. "
            "3) Complete your profile with your name, company, and preferences. "
            "4) Choose your plan: Free (up to 3 users), Pro ($29/mo, up to 25 users), "
            "or Enterprise (custom pricing, unlimited users). "
            "5) Set up two-factor authentication for security. "
            "To update your profile: Account Settings → Profile → Edit. "
            "To change your email: Account Settings → Email → Verify New Email. "
            "For team accounts, invite members via Settings → Team Management → Add Member."
        ),
    },
    {
        "title": "Account Deactivation & Data Deletion",
        "category": "account",
        "content": (
            "To deactivate your account: 1) Go to Account Settings → Account → Deactivate Account. "
            "2) Choose between temporary deactivation (can reactivate within 90 days) or "
            "permanent deletion (irreversible after 30-day grace period). "
            "3) Before deleting, export your data via Settings → Data Export → Download All. "
            "4) Active subscriptions must be cancelled before deactivation. "
            "5) Team owners must transfer ownership before deleting their account. "
            "Data is retained for 30 days after deletion request per our data retention policy. "
            "To request immediate data deletion under GDPR, email privacy@example.com."
        ),
    },
    {
        "title": "Account Security Best Practices",
        "category": "account",
        "content": (
            "Protect your account: 1) Use a unique, strong password (12+ characters). "
            "2) Enable two-factor authentication (2FA). "
            "3) Review active sessions regularly: Settings → Security → Active Sessions. "
            "4) Sign out of devices you don't recognize. "
            "5) Never share your login credentials or API keys. "
            "6) Check for suspicious activity in your account's audit log. "
            "If you suspect unauthorized access: 1) Change your password immediately. "
            "2) Revoke all active sessions. 3) Contact support for an account security review."
        ),
    },

    # ---- BILLING ----
    {
        "title": "Billing & Refund Policy",
        "category": "billing",
        "content": (
            "Refund Policy: We offer full refunds within 30 days of purchase. "
            "After 30 days, we can offer prorated credit toward your account. "
            "To request a refund: 1) Go to Account Settings → Billing → View Invoices. "
            "2) Click 'Request Refund' on the relevant invoice. "
            "3) Provide a brief reason for the refund request. "
            "4) Refunds are processed within 5-7 business days to your original payment method. "
            "For overcharges or billing errors, contact us and we'll resolve it within 24 hours. "
            "Enterprise customers: contact your account manager for refund requests."
        ),
    },
    {
        "title": "Subscription Plans & Pricing",
        "category": "billing",
        "content": (
            "Our plans: "
            "FREE PLAN — Up to 3 users, 1GB storage, basic features, community support. "
            "PRO PLAN ($29/month billed monthly, $24/month billed annually) — Up to 25 users, "
            "50GB storage, advanced analytics, priority support, API access. "
            "ENTERPRISE PLAN (custom pricing) — Unlimited users, unlimited storage, dedicated "
            "account manager, SSO, custom integrations, 24/7 phone support, SLA guarantee. "
            "All plans include a 14-day free trial with no credit card required. "
            "To compare plans: visit example.com/pricing. "
            "Volume discounts available for 50+ seats — contact sales@example.com."
        ),
    },
    {
        "title": "Subscription Management — Upgrade, Downgrade, Cancel",
        "category": "billing",
        "content": (
            "To upgrade: Account Settings → Billing → Change Plan → select new plan. "
            "Upgrades take effect immediately; you're charged the prorated difference. "
            "To downgrade: Same path, select a lower plan. Downgrades take effect at the "
            "end of your current billing cycle. Check feature limitations before downgrading. "
            "To cancel: Account Settings → Billing → Cancel Subscription. "
            "After cancellation, you retain access until the end of the billing period. "
            "Data is preserved for 90 days after cancellation. "
            "To reactivate: Sign in and go to Billing → Reactivate (within 90 days). "
            "Annual plans can be cancelled with a prorated refund for remaining months."
        ),
    },
    {
        "title": "Payment Methods & Invoice Management",
        "category": "billing",
        "content": (
            "Accepted payment methods: Visa, Mastercard, American Express, PayPal, wire transfer "
            "(Enterprise only). To update your payment method: Billing → Payment Method → Update Card. "
            "Invoices are generated on the 1st of each month and emailed to your billing contact. "
            "To download invoices: Billing → Invoice History → Download PDF. "
            "To add a tax ID (VAT/GST): Billing → Tax Information → Add Tax ID. "
            "If payment fails: 1) We retry 3 times over 7 days. 2) After 3 failed attempts, "
            "your account enters a 14-day grace period. 3) After grace period, account is suspended. "
            "Update payment info to restore access immediately."
        ),
    },
    {
        "title": "Billing Disputes & Unexpected Charges",
        "category": "billing",
        "content": (
            "If you see an unexpected charge: 1) Check Billing → Invoice History for details. "
            "2) Common causes: plan auto-renewal, usage overage, add-on features, tax changes. "
            "3) If the charge is incorrect, contact billing support with your invoice number. "
            "We respond to billing disputes within 1 business day. "
            "For fraud/unauthorized charges: 1) Change your password immediately. "
            "2) Contact us at billing@example.com with 'URGENT' in the subject. "
            "3) We'll investigate and issue a refund within 48 hours if confirmed fraudulent. "
            "Note: Chargeback disputes through your bank may result in account suspension."
        ),
    },

    # ---- TECHNICAL ----
    {
        "title": "General Troubleshooting Guide",
        "category": "technical",
        "content": (
            "Common troubleshooting steps: 1) Clear browser cache and cookies. "
            "2) Try a different browser (Chrome, Firefox, Edge recommended). "
            "3) Disable browser extensions that might interfere. "
            "4) Check our status page at status.example.com for outages. "
            "5) Try incognito/private browsing mode. "
            "6) Ensure JavaScript is enabled in your browser settings. "
            "7) Check if your network/firewall is blocking our domain. "
            "If the issue persists, send us a screenshot, your browser version, "
            "and OS version. You can find this info at about:version in Chrome."
        ),
    },
    {
        "title": "API Documentation & Common Errors",
        "category": "technical",
        "content": (
            "API Base URL: https://api.example.com/v1 "
            "Authentication: Include 'Authorization: Bearer YOUR_API_KEY' in headers. "
            "Rate limit: 100 requests/minute (Pro), 1000/minute (Enterprise). "
            "Common API errors: "
            "401 Unauthorized — Invalid or expired API key. Regenerate at Settings → API Keys. "
            "403 Forbidden — Your plan doesn't include API access (Pro+ required). "
            "429 Too Many Requests — Rate limit exceeded. Implement exponential backoff. "
            "500 Internal Error — Server issue on our end. Check status.example.com and retry. "
            "For webhook setup: Settings → Integrations → Webhooks → Add Endpoint."
        ),
    },
    {
        "title": "Performance & Speed Issues",
        "category": "technical",
        "content": (
            "If the app is slow: 1) Check your internet connection speed at speedtest.net. "
            "2) Close unnecessary browser tabs (each tab uses memory). "
            "3) Clear browser cache: Settings → Clear Browsing Data → Cached Images/Files. "
            "4) Check our status page for any performance degradation reports. "
            "5) Try reducing the number of items per page in your dashboard settings. "
            "For slow API responses: Check the response time header 'X-Response-Time'. "
            "If consistently over 2 seconds, contact support with the request ID from "
            "the 'X-Request-ID' header. Our SLA guarantees 99.9% uptime for Enterprise plans."
        ),
    },
    {
        "title": "Third-Party Integrations",
        "category": "technical",
        "content": (
            "Supported integrations: Slack, Microsoft Teams, Jira, Salesforce, Zapier, "
            "HubSpot, Zendesk, GitHub, Google Workspace. "
            "To connect an integration: Settings → Integrations → Browse → Connect. "
            "Slack integration: Receive real-time notifications for ticket updates. "
            "Jira integration: Auto-create Jira issues from support tickets. "
            "Zapier integration: Build custom workflows with 5000+ apps. "
            "To disconnect: Settings → Integrations → Connected → Disconnect. "
            "If an integration stops working: 1) Disconnect and reconnect. "
            "2) Check that your API tokens haven't expired. 3) Contact support."
        ),
    },
    {
        "title": "Mobile App Issues",
        "category": "technical",
        "content": (
            "Mobile app available for iOS 15+ and Android 10+. "
            "Download from App Store or Google Play: search 'Example Support'. "
            "Common mobile issues: "
            "App won't open: Force close and reopen. If it persists, uninstall and reinstall. "
            "Push notifications not working: Check phone's notification settings for our app. "
            "Login issues on mobile: Try 'Sign in with Google/Apple' instead of email/password. "
            "Offline mode: The app caches your recent data. Sync happens when back online. "
            "To report a mobile bug: Settings → Help → Report Bug (includes device info automatically)."
        ),
    },
    {
        "title": "Data Import & Export",
        "category": "technical",
        "content": (
            "To import data: Settings → Data → Import → Upload CSV/JSON file. "
            "Supported import formats: CSV, JSON, XML. Max file size: 100MB. "
            "Template files available at example.com/import-templates. "
            "To export data: Settings → Data → Export → Choose format (CSV, JSON, PDF). "
            "Export includes: tickets, customers, analytics, and knowledge base articles. "
            "Exports are generated within 5 minutes and emailed to you. "
            "Bulk export via API: GET /api/v1/export?format=csv&type=tickets. "
            "GDPR data portability requests: email privacy@example.com for a full data package."
        ),
    },

    # ---- PRODUCT ----
    {
        "title": "Dashboard & Analytics Overview",
        "category": "product",
        "content": (
            "Your dashboard shows key metrics: total tickets, open/resolved/escalated counts, "
            "resolution rate, average response time, and customer satisfaction scores. "
            "Time filters: Today, This Week, This Month, Custom Range. "
            "Charts include: Ticket Volume Over Time, Priority Breakdown, Category Distribution, "
            "Agent Performance, and Customer Sentiment Trends. "
            "To customize your dashboard: Click 'Edit Dashboard' → drag and rearrange widgets. "
            "Export reports: Click the Export button on any chart for CSV/PDF. "
            "Scheduled reports: Settings → Reports → Create Schedule → Choose frequency (daily/weekly/monthly)."
        ),
    },
    {
        "title": "Ticket Management Best Practices",
        "category": "product",
        "content": (
            "Effective ticket management: "
            "1) Triage incoming tickets by priority — urgent and high-priority first. "
            "2) Use categories (billing, technical, account, product) for organized routing. "
            "3) Set SLA targets: urgent = 1 hour, high = 4 hours, medium = 24 hours, low = 48 hours. "
            "4) Use internal notes (visible only to agents) for team communication. "
            "5) Merge duplicate tickets from the same customer about the same issue. "
            "6) Use ticket templates for common responses to save time. "
            "7) Review escalated tickets daily to prevent customer frustration. "
            "8) Close resolved tickets after 7 days of no customer response."
        ),
    },
    {
        "title": "Knowledge Base Management",
        "category": "product",
        "content": (
            "Building an effective knowledge base: "
            "1) Write articles for your most common customer questions. "
            "2) Use clear, step-by-step instructions with screenshots. "
            "3) Organize by category: Getting Started, Account, Billing, Technical, FAQ. "
            "4) Keep articles updated — review quarterly for accuracy. "
            "5) Use internal articles for agent-only reference material. "
            "To create an article: Knowledge Base → New Article → Choose category. "
            "To update: Click Edit on any article. Changes are saved as versions. "
            "SEO: Articles are searchable by customers on your help center at help.example.com."
        ),
    },
    {
        "title": "Automation & Workflow Rules",
        "category": "product",
        "content": (
            "Set up automation rules: Settings → Automation → Create Rule. "
            "Trigger conditions: ticket created, status changed, priority set, keyword match. "
            "Possible actions: assign to agent, change priority, send notification, add tag. "
            "Example rules: "
            "1) IF priority = urgent AND sentiment = angry THEN notify manager via Slack. "
            "2) IF category = billing THEN assign to billing team. "
            "3) IF no response in 48 hours THEN send follow-up email. "
            "4) IF ticket resolved for 7 days THEN auto-close. "
            "Rules are processed in order; drag to reorder. Max 50 rules per account."
        ),
    },
    {
        "title": "Customer Satisfaction Surveys (CSAT)",
        "category": "product",
        "content": (
            "CSAT surveys are automatically sent when a ticket is resolved. "
            "Customers rate their experience from 1-5 stars and can leave a comment. "
            "To configure: Settings → Surveys → CSAT Settings. "
            "Options: Enable/disable auto-send, customize survey message, set delay "
            "(send immediately, 1 hour after, or 24 hours after resolution). "
            "View results: Analytics → Customer Satisfaction → CSAT Scores. "
            "Benchmark: Industry average is 4.0/5.0. Our recommended target is 4.5+. "
            "Tips: Respond quickly, be empathetic, solve issues in first contact when possible."
        ),
    },

    # ---- SHIPPING & ORDERS ----
    {
        "title": "Shipping & Delivery Information",
        "category": "shipping",
        "content": (
            "Shipping options: "
            "Standard shipping: 5-7 business days ($5.99 or free over $50). "
            "Express shipping: 2-3 business days ($12.99). "
            "Overnight shipping: Next business day ($24.99). "
            "International shipping: 10-15 business days (varies by country). "
            "Track your order: Go to Orders → click your order → 'Track Package'. "
            "You'll receive a tracking email with carrier link when shipped. "
            "If your package hasn't arrived within the expected timeframe: "
            "1) Check the tracking status for updates. "
            "2) Verify the shipping address is correct. "
            "3) Contact us if tracking shows 'delivered' but you haven't received it."
        ),
    },
    {
        "title": "Returns & Exchanges",
        "category": "shipping",
        "content": (
            "Return policy: Items can be returned within 30 days of delivery. "
            "Items must be unused, in original packaging, with tags attached. "
            "To start a return: 1) Go to Orders → select order → 'Return Item'. "
            "2) Choose reason for return. 3) Print the prepaid return label. "
            "4) Ship item back within 14 days. 5) Refund processed within 5-7 business days "
            "after we receive the item. "
            "Exchanges: Select 'Exchange' instead of 'Return' to swap for a different size/color. "
            "Non-returnable items: Gift cards, personalized items, digital downloads, sale items (final sale). "
            "International returns: Customer pays return shipping costs."
        ),
    },
    {
        "title": "Order Issues — Wrong Item, Damaged, Missing",
        "category": "shipping",
        "content": (
            "Wrong item received: 1) Take a photo of the item received and the packing slip. "
            "2) Contact support with order number and photos. "
            "3) We'll ship the correct item immediately at no extra cost. "
            "4) Keep the wrong item or donate it — no need to return. "
            "Damaged item: 1) Take photos of the damage and packaging. "
            "2) Contact support within 48 hours of delivery. "
            "3) We'll send a replacement or issue a full refund. "
            "Missing items from order: Check if the order is shipping in multiple packages "
            "(you'll see multiple tracking numbers). If items are truly missing, contact us."
        ),
    },
    {
        "title": "Order Cancellation & Modification",
        "category": "shipping",
        "content": (
            "To cancel an order: Orders → select order → 'Cancel Order'. "
            "Cancellation is only possible if the order hasn't shipped yet. "
            "Window: Most orders can be cancelled within 1 hour of placing. "
            "After shipping: You'll need to wait for delivery and then initiate a return. "
            "To modify an order (change size, color, quantity, address): "
            "1) If not yet shipped: Contact support immediately with your order number and changes. "
            "2) If already shipped: We cannot modify — please return and reorder. "
            "Refunds for cancelled orders are processed within 3-5 business days."
        ),
    },

    # ---- GENERAL ----
    {
        "title": "Contact Us & Support Hours",
        "category": "general",
        "content": (
            "Support channels: "
            "Email: support@example.com (24/7, response within 4 hours). "
            "Live Chat: Available on our website Mon-Fri, 9 AM - 6 PM EST. "
            "Phone: +1-800-EXAMPLE (Mon-Fri, 9 AM - 5 PM EST, Enterprise only). "
            "Twitter/X: @ExampleSupport for quick questions. "
            "Help Center: help.example.com for self-service articles. "
            "For urgent issues outside business hours, email with 'URGENT' in subject. "
            "Average response times: Email 2-4 hours, Chat 5 minutes, Phone instant."
        ),
    },
    {
        "title": "Privacy Policy & Data Protection",
        "category": "general",
        "content": (
            "We take your privacy seriously. Key points: "
            "1) We collect only data necessary to provide our services. "
            "2) Your data is encrypted at rest (AES-256) and in transit (TLS 1.3). "
            "3) We never sell your data to third parties. "
            "4) You can export or delete your data at any time (Settings → Privacy). "
            "5) GDPR, CCPA, and SOC 2 Type II compliant. "
            "6) Data is stored in US-East and EU-West data centers. "
            "7) Our DPO can be reached at privacy@example.com. "
            "Full privacy policy: example.com/privacy. Cookie policy: example.com/cookies."
        ),
    },
    {
        "title": "Feature Requests & Product Feedback",
        "category": "general",
        "content": (
            "We love hearing from our users! Submit feature requests: "
            "1) In-app: Help → Suggest a Feature. "
            "2) Feedback portal: feedback.example.com — vote on existing ideas or add new ones. "
            "3) Community forum: community.example.com — discuss with other users and our team. "
            "How we prioritize: Requests are reviewed monthly by our product team. "
            "High-vote features are added to our public roadmap at example.com/roadmap. "
            "You'll receive an email notification when your requested feature is released. "
            "Beta features: Opt in at Settings → Labs to try new features before general release."
        ),
    },
    {
        "title": "Service Status & Outage Information",
        "category": "general",
        "content": (
            "Check real-time service status: status.example.com. "
            "Subscribe to status updates: Click 'Subscribe' on the status page for email/SMS alerts. "
            "During an outage: 1) Check status page for estimated resolution time. "
            "2) Follow @ExampleStatus on Twitter for real-time updates. "
            "3) Do NOT create support tickets for known outages — it slows down resolution. "
            "After an outage: We publish a post-mortem report within 48 hours. "
            "Uptime SLA credits: If monthly uptime drops below 99.9%, Enterprise customers "
            "are eligible for service credits (10% for each 0.1% below SLA)."
        ),
    },
    {
        "title": "Email Notifications & Preferences",
        "category": "general",
        "content": (
            "Manage your email notifications: Settings → Notifications → Email Preferences. "
            "Notification types: "
            "- Ticket updates: When a ticket you created or follow gets a response. "
            "- System alerts: Service outages, maintenance windows, security notices. "
            "- Product updates: New features, release notes, blog posts. "
            "- Billing: Payment receipts, upcoming renewal, failed payment alerts. "
            "To unsubscribe from marketing emails: Click 'Unsubscribe' at the bottom of any email. "
            "To unsubscribe from all: Settings → Notifications → Unsubscribe All "
            "(except critical security alerts). "
            "Digest mode: Receive a daily summary instead of individual emails."
        ),
    },
    {
        "title": "Multi-Language & Localization Support",
        "category": "general",
        "content": (
            "Supported languages: English, Spanish, French, German, Portuguese, Japanese, "
            "Chinese (Simplified), Korean, Hindi, Arabic. "
            "To change language: Settings → Preferences → Language. "
            "Help center articles are available in English, Spanish, and French. "
            "AI agent supports: English (primary), with experimental support for 9 additional languages. "
            "RTL (right-to-left) support: Available for Arabic and Hebrew interfaces. "
            "To request a new language: Submit a feature request at feedback.example.com. "
            "Translation contributions are welcome via our open-source translation project on GitHub."
        ),
    },
]


# =============================================================================
# Chunking (for splitting long articles into smaller pieces)
# =============================================================================

def chunk_text(text: str, max_chunk_size: int = 500) -> list[str]:
    """
    Split article text into smaller chunks for embedding.
    
    WHY CHUNK:
        - Embedding models have a context window (~256 tokens for MiniLM)
        - Smaller chunks = more precise retrieval
        - A query about "password reset" should match the password-specific
          paragraph, not a 2000-word article about everything
    
    STRATEGY:
        Split on sentence boundaries ('. '), then combine sentences
        until we reach max_chunk_size. This preserves meaning better
        than splitting at arbitrary character positions.
    """
    # For our articles (mostly 200-500 chars each), most will be a single chunk.
    # This future-proofs for longer articles.
    if len(text) <= max_chunk_size:
        return [text]
    
    sentences = text.replace('. ', '.\n').split('\n')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
            current_chunk = f"{current_chunk} {sentence}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks if chunks else [text]


# =============================================================================
# Seed Function
# =============================================================================

async def seed_knowledge_base():
    """
    Seed the knowledge base with articles and their vector embeddings.
    
    Steps:
        1. Clear existing articles and embeddings (fresh seed)
        2. Insert each article into knowledge_articles
        3. Chunk each article's content
        4. Embed each chunk using sentence-transformers
        5. Insert chunks + embeddings into kb_embeddings
    """
    from src.db.session import async_session_factory, init_db, engine
    from src.db.models import KnowledgeArticle, KBEmbedding
    from src.services.embedding_service import embedding_service
    
    print("🔧 Initializing database...")
    await init_db()
    
    print("📦 Loading embedding model (first run downloads ~90MB)...")
    embedding_service.load_model()
    dimension = embedding_service.get_dimension()
    print(f"   Model loaded. Embedding dimension: {dimension}")
    
    async with async_session_factory() as session:
        # Step 1: Drop and recreate kb_embeddings to ensure the 'embedding'
        # vector column exists. create_all() won't ALTER existing tables,
        # so if the table was created before we added the column, it's missing.
        print("\n🗑️  Dropping and recreating KB tables...")
        await session.execute(text("DROP TABLE IF EXISTS kb_embeddings CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS knowledge_articles CASCADE"))
        await session.commit()
    
    # Recreate the tables with the new schema (including the vector column)
    from src.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("   Tables recreated with vector column ✓")
    
    async with async_session_factory() as session:
        
        # Step 2-5: Insert articles with embeddings using ORM objects
        # (ORM handles all type conversions — avoids asyncpg parameter issues)
        total_chunks = 0
        
        for i, article in enumerate(KB_ARTICLES, 1):
            # Create the article ORM object
            db_article = KnowledgeArticle(
                title=article["title"],
                content=article["content"],
                category=article["category"],
            )
            session.add(db_article)
            await session.flush()  # Flush to get the generated UUID
            
            # Chunk the article content
            chunks = chunk_text(article["content"])
            
            # Embed all chunks in batch (much faster than one-by-one)
            embeddings = embedding_service.embed_texts(chunks)
            
            # Insert each chunk with its embedding as ORM objects
            for chunk_idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                db_embedding = KBEmbedding(
                    article_id=db_article.id,
                    chunk_text=chunk,
                    chunk_index=chunk_idx,
                    embedding=embedding,
                )
                session.add(db_embedding)
                total_chunks += 1
            
            print(f"   [{i:2d}/{len(KB_ARTICLES)}] {article['title']} → {len(chunks)} chunk(s)")
        
        await session.commit()
    
    print(f"\n✅ Knowledge base seeded successfully!")
    print(f"   Articles: {len(KB_ARTICLES)}")
    print(f"   Chunks:   {total_chunks}")
    print(f"   Vector dimension: {dimension}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
