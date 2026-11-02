"""Kestrel Budget: a fictional personal budgeting app. Held-out set.

Written before any model ran on it; prompts, thresholds and the regression
rule were not changed after scoring it. Planted story, by release:

- 3.0  baseline. The app is slow to open (complaints in about one item in six).
- 3.1  a copy-paste campaign: five near-identical reviews about ads.
- 3.2  performance work fixes the slow start. A bank-connection change breaks
       account syncing for many users (regression).
- 3.3  bank connections fixed. A press article doubles the review volume;
       pricing complaints rise in count but not in rate.
- 3.4  receipt scanning starts crashing (regression). Shared budgets launch
       with a few complaints in a 50-item release.

Charts and spending reports are praised in every release.
"""

SPEC = {
    "id": "kestrel",
    "name": "Kestrel Budget",
    "description": "Kestrel Budget is a fictional personal budgeting app that connects to bank accounts. "
                   "Held-out set: not used for tuning.",
    "product": "Kestrel Budget, a personal budgeting app",
    "id_prefix": "KB",
    "seed": 3307,
    "ticket_share": 0.1,
    "stale_share": 0.05,
    "missing_version_share": 0.18,
    "last_window_days": 15,
    "releases": [
        {"version": "3.0", "date": "2026-02-09", "volume": 55,
         "notes": "Spending reports, receipt scanning, bill alerts."},
        {"version": "3.1", "date": "2026-03-16", "volume": 60,
         "notes": "Free tier with ads; budget categories redesign."},
        {"version": "3.2", "date": "2026-04-20", "volume": 65,
         "notes": "Faster start-up; migration to a new bank-connection provider."},
        {"version": "3.3", "date": "2026-05-25", "volume": 110,
         "notes": "Bank connection fixes. Covered in a national newspaper's money section."},
        {"version": "3.4", "date": "2026-06-29", "volume": 50,
         "notes": "Shared budgets; new camera module for receipt scanning."},
    ],
    # Planted mentions per release (3.0, 3.1, 3.2, 3.3, 3.4).
    "counts": {
        "bank_sync": {"negative": [3, 3, 18, 3, 2], "positive": [2, 2, 1, 4, 2]},
        "receipts": {"negative": [2, 2, 2, 3, 10], "positive": [3, 3, 3, 6, 2]},
        "reports": {"negative": [1, 1, 1, 2, 1], "positive": [8, 9, 10, 16, 7]},
        "speed": {"negative": [10, 10, 2, 3, 1], "positive": [0, 0, 3, 3, 1]},
        "pricing": {"negative": [5, 5, 5, 9, 4], "positive": [1, 1, 1, 1, 0]},
        "budgets": {"negative": [2, 2, 2, 4, 2], "positive": [4, 4, 5, 8, 3], "neutral": [1, 1, 1, 2, 1]},
        "ads": {"negative": [0, 1, 1, 1, 0]},
        "shared_budgets": {"negative": [0, 0, 0, 0, 3], "positive": [0, 0, 0, 0, 2]},
        "bill_alerts": {"negative": [2, 2, 2, 3, 1], "positive": [1, 1, 1, 2, 1]},
        "export": {"negative": [1, 1, 1, 1, 1], "neutral": [1, 2, 1, 2, 1]},
        "app_lock": {"negative": [1, 1, 1, 2, 1], "positive": [2, 2, 2, 3, 1]},
    },
    "gold": {
        "regressions": [{"release": "3.2", "feature": "bank_sync"}, {"release": "3.4", "feature": "receipts"}],
        "improvements": [{"release": "3.2", "feature": "speed"}, {"release": "3.3", "feature": "bank_sync"}],
        "praised": ["reports"],
        "traps": [
            {"release": "3.3", "feature": "pricing", "kind": "volume_spike",
             "note": "Complaint count nearly doubles with review volume; the rate is flat."},
            {"release": "3.1", "feature": "ads", "kind": "duplicate_burst",
             "note": "A copy-paste campaign of five reviews; counted once it is two complaints."},
            {"release": "3.4", "feature": "shared_budgets", "kind": "small_sample",
             "note": "New feature, 3 complaints in a 50-item release."},
        ],
    },
    "slots": {
        "device": ["iPhone 16", "iPhone 14", "Pixel 7", "Pixel 9 Pro", "Galaxy S23", "Galaxy A35", "Moto G",
                   "iPhone 12 mini"],
        "bank": ["my credit union", "Northgate Bank", "my savings bank", "Harbour Federal", "my main bank"],
        "seconds": ["10", "15", "20", "30"],
        "days": ["three days", "a week", "since Monday", "two weeks"],
        "price": ["$5.99", "$6.49", "$59 a year"],
    },
    "features": {
        "bank_sync": {
            "name": "Bank connection",
            "description": "Linking bank accounts and importing transactions.",
            "neg": [
                "My bank account won't connect anymore.",
                "Transactions from {bank} stopped importing after the update.",
                "It keeps asking me to re-link {bank} and then fails.",
                "Bank sync has been broken for {days}.",
                "No new transactions since the update, the connection just errors out.",
                "Linking my account gives 'connection failed' every time.",
                "The bank feed is stuck on last month's balance.",
                "Re-authorised {bank} three times, still no transactions.",
                "My card transactions are missing, the bank link is broken.",
                "bank connection keeps dropping, useless without it",
                "Accounts show 'needs attention' and never refresh.",
                "Half my accounts disconnected after updating.",
                "It imports duplicate transactions from {bank} and then stops syncing.",
                "~Haven't seen a single new transaction since Tuesday even though I've used my card every day.",
                "~Fantastic, my balance is a week old again.",
                "~bank conection keeps failng",
                "~I keep re-entering my bank password and nothing comes through.",
            ],
            "pos": [
                "Connecting {bank} took less than a minute.",
                "Transactions import reliably every morning.",
                "The bank connection is rock solid.",
                "~My card purchases show up within minutes.",
            ],
            "ticket_neg": [
                "Bank connection fails with 'provider error' after updating to {version_seen}. Bank: {bank}. "
                "Device: {device}. Re-linking does not help.",
                "Transactions not imported since migration to the new provider. Accounts stuck on 'syncing'. "
                "{version_seen}.",
                "OAuth re-link loop for {bank}. After approving in the bank app the user is sent back to the "
                "link screen. {version_seen}, {device}.",
            ],
        },
        "receipts": {
            "name": "Receipt scanning",
            "description": "Photographing receipts and reading their totals.",
            "neg": [
                "The receipt scanner crashes as soon as the camera opens.",
                "Scanning a receipt closes the app.",
                "Receipt photos come out blurry and the total is read wrong.",
                "Camera freezes on the receipt screen.",
                "Since the update I can't scan receipts at all.",
                "It reads the date on my receipt as the total.",
                "receipt scanning crashes every time on my {device}",
                "Tapping 'scan receipt' gives a black screen and then it quits.",
                "The scanner can't find the edges of the receipt.",
                "Receipt capture is broken, it just shuts down.",
                "~Every time I point the camera at a receipt the whole thing quits.",
                "~Thanks for the update that made photographing receipts impossible.",
                "~reciept scaner crashs",
            ],
            "pos": [
                "Receipt scanning is magic, it reads the total perfectly.",
                "Snapping a photo of a receipt and having it filed is great.",
                "The receipt scanner saves me so much typing.",
                "I love that it reads the shop name off the receipt.",
                "~No more typing in totals from paper slips.",
            ],
            "ticket_neg": [
                "Crash when opening the receipt camera on {version_seen}. Device: {device}. Reproducible 100%.",
                "Receipt scan returns black preview and the app terminates. {device}, {version_seen}.",
                "OCR reads wrong total on receipts with discounts. {version_seen}.",
            ],
        },
        "reports": {
            "name": "Charts and spending reports",
            "description": "Charts, monthly reports and spending insights.",
            "neg": [
                "The monthly report double counts transfers.",
                "Charts don't let me pick a custom date range.",
            ],
            "pos": [
                "The spending charts are beautiful and clear.",
                "Monthly reports showed me exactly where my money goes.",
                "Love the pie chart by category.",
                "The insights screen is the best part of the app.",
                "Reports make it obvious when I'm overspending.",
                "The yearly overview chart is brilliant.",
                "I check the spending trends every week, so useful.",
                "Best charts of any budgeting app I've used.",
                "The weekly spending summary is really helpful.",
                "the reports are clear even for someone bad with numbers",
                "Seeing my spending graphed by month changed my habits.",
                "The category breakdown chart is super clear.",
                "~Seeing where my money went each month in one picture is brilliant.",
                "~The graphs are not bad at all.",
            ],
        },
        "speed": {
            "name": "Speed and start-up",
            "description": "How fast the app opens and responds.",
            "neg": [
                "Takes {seconds} seconds to open.",
                "The app is so slow to start.",
                "Every screen takes ages to load.",
                "Opening the app shows a spinner for ages.",
                "It's sluggish, scrolling transactions stutters.",
                "Slow slow slow. I just want to check my balance.",
                "Startup is painfully slow on my {device}.",
                "Loading the dashboard takes forever.",
                "So laggy that I gave up checking it at the till.",
                "the app takes forever to launch",
                "~I could make a coffee in the time it takes to open.",
                "~Love staring at the loading spinner every morning. Not.",
            ],
            "pos": [
                "Opens instantly now, much faster than before.",
                "The speed improvement in this update is huge.",
                "App launches in a second now.",
                "~It's not sluggish anymore.",
            ],
            "ticket_neg": [
                "Cold start takes {seconds}s on {device}. Profiling shows the transaction list loads before the "
                "first frame. {version_seen}.",
            ],
        },
        "pricing": {
            "name": "Pricing and subscription",
            "description": "Premium price, subscription and paywall.",
            "neg": [
                "Premium at {price} is too pricey for a budgeting app.",
                "The free version is too limited now.",
                "Paywalled half the features, really?",
                "Subscription is too expensive.",
                "Ironic that a budgeting app costs this much.",
                "Price went up without warning.",
                "Too many features locked behind premium.",
                "~Six dollars a month to tell me I spend too much.",
            ],
            "pos": [
                "Premium is worth every cent.",
            ],
        },
        "budgets": {
            "name": "Budgets and categories",
            "description": "Setting budgets and categorising spending.",
            "neg": [
                "Can't create my own categories.",
                "Budgets reset on the wrong day of the month.",
                "Auto-categorising puts groceries under entertainment.",
                "Moving a transaction to another category is fiddly.",
                "~Groceries keep ending up under entertainment.",
            ],
            "pos": [
                "Setting a monthly budget is easy.",
                "The category budgets keep me on track.",
                "Love the envelope-style budgets.",
                "Auto-categorisation is surprisingly accurate.",
                "Rollover budgets are exactly what I wanted.",
            ],
            "req": [
                "Please let budgets start on payday instead of the 1st.",
                "Would love sub-categories.",
            ],
            "ticket_req": [
                "Feature request: custom budget period aligned to payday.",
            ],
        },
        "ads": {
            "name": "Ads",
            "description": "Advertising in the free tier.",
            "neg": [
                "Too many ads in the free version.",
                "A full-screen ad every time I add an expense.",
            ],
        },
        "shared_budgets": {
            "name": "Shared budgets",
            "description": "Budgets shared with a partner or household.",
            "neg": [
                "Shared budget with my partner doesn't show her transactions.",
                "The invite link for shared budgets never arrives.",
                "Shared budgets double count our joint account.",
            ],
            "pos": [
                "Shared budgets with my husband is a great addition.",
                "Finally we can budget together as a couple.",
            ],
            "ticket_neg": [
                "Shared budget invite email not delivered. {version_seen}.",
            ],
        },
        "bill_alerts": {
            "name": "Bill alerts",
            "description": "Reminders for upcoming bills.",
            "neg": [
                "Bill reminders come a day after the bill is paid.",
                "I never get the bill alerts even though they're switched on.",
                "Bill alerts fire for bills I've already cancelled.",
                "~Found out my phone bill was due from the late fee, not from the app.",
            ],
            "pos": [
                "The bill alerts have saved me from late fees.",
                "Love getting a heads-up before rent goes out.",
            ],
            "ticket_neg": [
                "Bill alert notifications not delivered on {device}. {version_seen}.",
            ],
        },
        "export": {
            "name": "Export",
            "description": "Exporting transactions to CSV or spreadsheets.",
            "neg": [
                "CSV export has the wrong date format.",
                "Export to spreadsheet drops the category column.",
            ],
            "req": [
                "Please add export to Excel.",
                "I need a way to export a year of transactions for my accountant.",
            ],
            "ticket_req": [
                "Feature request: scheduled monthly CSV export by email.",
            ],
        },
        "app_lock": {
            "name": "App lock and Face ID",
            "description": "Passcode and biometric lock for opening the app.",
            "neg": [
                "Face ID unlock fails half the time.",
                "The passcode screen appears twice.",
            ],
            "pos": [
                "Face ID lock makes me feel safe.",
                "Love the passcode lock, my kids can't see my spending.",
                "Fingerprint unlock is quick.",
                "~Nobody can snoop on my spending when they borrow my phone.",
            ],
        },
    },
    "duplicates": [
        {
            "id": "ads-campaign",
            "release": "3.1",
            "feature": "ads",
            "polarity": "negative",
            "copies": [
                "Ads ads ads. Every single screen now has an advert, this used to be a clean app. "
                "Uninstalling until the ads are gone.",
                "Ads ads ads! Every single screen now has an advert, this used to be a clean app. "
                "Uninstalling until the ads are gone!",
                "ads ads ads. every single screen now has an advert, this used to be a clean app. "
                "uninstalling until the ads are gone.",
                "Ads, ads, ads. Every single screen now has an advert, this used to be a clean app. "
                "Uninstalling until the ads are gone.",
                "Ads ads ads. Every single screen now has an advert, this used to be a clean app. "
                "Uninstalling until the ads are gone...",
            ],
            "sources": ["play_store", "play_store", "app_store", "play_store", "app_store"],
        },
    ],
    "noise_weights": {"generic_positive": 0.6, "generic_negative": 0.2, "off_topic": 0.15, "spam": 0.05},
    "noise": {
        "generic_positive": [
            "Good app.", "Really helpful app!", "Five stars.", "Does the job.", "Very good app.",
            "Changed how I handle money.", "Good app.", "Excellent.", "Recommended it to all my friends.",
            "Nice and simple.", "Super useful.", "Great budgeting app.", "Love this app.",
        ],
        "generic_negative": [
            "Not impressed.", "Uninstalled.", "Bit of a let down.", "Two stars.", "Could be better.",
            "Not great.",
        ],
        "off_topic": [
            "Writing this on the bus, hi mum",
            "This review is for my school project",
            "Does anyone know a good pizza place downtown?",
            "Rated by mistake.",
            "Can't believe it's raining again.",
        ],
        "spam": [
            "Crypto signals in my profile, 10x guaranteed",
            "Win a free phone, visit my page",
        ],
        "ticket_noise": [
            "Closing as duplicate.",
            "Test issue from the QA team, ignore.",
            "Moved to the website repository.",
        ],
    },
}
