"""Tallynote: a fictional notes and to-do app. Development set.

Prompts, clustering thresholds and the regression rule were tuned on this app
only. Planted story, by release:

- 2.0  baseline. Sync is slow (complaints in about one item in five).
- 2.1  login-loop regression: about 30% of items complain about sign-in.
- 2.2  new sync engine and a login fix: both complaints fall back. One user
       posts the same dark-mode rant five times (two stores and the tracker).
- 2.3  featured in the store: volume doubles. Reminders stop firing
       (regression). Search complaints double in count but not in rate.
- 2.4  reminders fixed. New home-screen widgets get a few complaints, but the
       release is two weeks old and has only 40 items.

Offline mode is praised in every release.
"""

SPEC = {
    "id": "tallynote",
    "name": "Tallynote",
    "description": "Tallynote is a fictional notes and to-do app for phones, tablets and laptops. "
                   "Development set: prompts and thresholds were tuned on it.",
    "product": "Tallynote, a notes and to-do app",
    "id_prefix": "TN",
    "seed": 2101,
    "ticket_share": 0.12,
    "stale_share": 0.06,
    "missing_version_share": 0.15,
    "last_window_days": 13,
    "releases": [
        {"version": "2.0", "date": "2026-03-02", "volume": 60,
         "notes": "Folders, checklists, offline editing."},
        {"version": "2.1", "date": "2026-04-06", "volume": 70,
         "notes": "New account system with Google and Apple sign-in."},
        {"version": "2.2", "date": "2026-05-11", "volume": 60,
         "notes": "Rewritten sync engine; fix for being signed out after updating; new dark theme."},
        {"version": "2.3", "date": "2026-06-15", "volume": 130,
         "notes": "Featured in the store. Reworked reminders and notification scheduling."},
        {"version": "2.4", "date": "2026-07-20", "volume": 40,
         "notes": "Home-screen widgets; reminder scheduling fix."},
    ],
    # Planted mentions per release (2.0, 2.1, 2.2, 2.3, 2.4).
    "counts": {
        "login": {"negative": [2, 21, 2, 4, 1], "positive": [1, 0, 1, 2, 1]},
        "sync": {"negative": [12, 14, 3, 4, 1], "positive": [0, 0, 4, 5, 2]},
        "offline": {"negative": [1, 0, 1, 1, 0], "positive": [9, 10, 9, 20, 6]},
        "search": {"negative": [4, 5, 4, 9, 3], "positive": [1, 1, 1, 3, 1]},
        "reminders": {"negative": [2, 2, 2, 23, 1], "positive": [2, 2, 2, 2, 1]},
        "dark_mode": {"negative": [1, 0, 1, 2, 1], "positive": [2, 2, 1, 3, 1]},
        "widgets": {"negative": [0, 0, 0, 0, 3], "positive": [0, 0, 0, 0, 2]},
        "pricing": {"negative": [3, 3, 3, 6, 2], "positive": [1, 0, 1, 1, 0]},
        "editor": {"negative": [2, 2, 2, 4, 1], "positive": [4, 4, 4, 8, 2]},
        "export": {"negative": [1, 1, 1, 2, 0], "neutral": [2, 2, 1, 3, 1]},
        "stability": {"negative": [2, 2, 2, 4, 1]},
        "sharing": {"neutral": [2, 2, 2, 3, 1], "positive": [0, 1, 0, 1, 0]},
    },
    "gold": {
        "regressions": [{"release": "2.1", "feature": "login"}, {"release": "2.3", "feature": "reminders"}],
        "improvements": [{"release": "2.2", "feature": "login"}, {"release": "2.2", "feature": "sync"},
                         {"release": "2.4", "feature": "reminders"}],
        "praised": ["offline"],
        "traps": [
            {"release": "2.3", "feature": "search", "kind": "volume_spike",
             "note": "Complaint count doubles because review volume doubles; the rate is flat."},
            {"release": "2.2", "feature": "dark_mode", "kind": "duplicate_burst",
             "note": "One rant posted five times; counted once it is two complaints."},
            {"release": "2.4", "feature": "widgets", "kind": "small_sample",
             "note": "New feature, 3 complaints in a 40-item release: worth watching, too thin to rank first."},
        ],
    },
    "slots": {
        "device": ["iPhone 15", "iPhone 13", "Pixel 8", "Pixel 9", "Galaxy S24", "Galaxy A54", "iPad Air",
                   "OnePlus 12", "iPhone SE"],
        "computer": ["laptop", "Mac", "Windows PC", "Chromebook", "work laptop"],
        "minutes": ["5", "10", "15", "20", "30"],
        "since": ["two days", "three days", "a week", "since Tuesday", "since the weekend"],
        "time": ["8am", "9am", "7:30", "noon", "6pm"],
    },
    "features": {
        "login": {
            "name": "Login and sign-in",
            "description": "Signing in, staying signed in, account access.",
            "neg": [
                "Since the update it keeps kicking me back to the sign-in screen.",
                "Stuck in a login loop: enter password, spinner, back to the login page.",
                "Can't log in anymore after updating, it just loops.",
                "It logged me out and now won't let me back in.",
                "I have to sign in every single time I open the app now.",
                "Google sign-in just bounces me back to the start screen.",
                "Login is broken. Tap sign in, nothing happens, back to the email screen.",
                "Reset my password twice and still can't get past the login.",
                "The sign in page just refreshes forever on my {device}.",
                "Apple sign-in says success and then asks me to sign in again.",
                "Locked out of my own notes for {since} because the login keeps looping.",
                "Every time I enter my password it flashes and returns to the sign in screen.",
                "can't get past sign in on my {device}, tried reinstalling",
                "Logging in is impossible since 2.1, it goes round in circles.",
                "~I typed my password five times today and I'm still looking at the welcome screen.",
                "~Great, another update and I'm locked out again. Love that for me.",
                "~Can't even get into my own account lol",
                "~signin broke agin after updte",
            ],
            "pos": [
                "Signing in with my Google account took two seconds.",
                "Login with Face ID is smooth.",
                "Love that I can sign in with Apple and skip another password.",
                "~Getting into my account is painless now.",
            ],
            "ticket_neg": [
                "Login loop after updating to {version_seen}. Device: {device}. Steps: open app, tap Sign in, "
                "enter credentials. Expected: notes list. Actual: returns to the sign-in screen.",
                "Users stuck on sign-in screen. After entering a valid password the app shows a spinner and "
                "goes back to the login form. Seen on {version_seen}, {device}.",
                "Google SSO redirects back to welcome screen ({version_seen}). Reproducible every time on {device}.",
                "Session lost after app update. Signed-in users are signed out and cannot sign in again. "
                "Version {version_seen}.",
            ],
        },
        "sync": {
            "name": "Sync",
            "description": "Syncing notes and lists between devices.",
            "neg": [
                "Sync takes forever, notes from my {computer} show up on my phone minutes later.",
                "Syncing between devices is painfully slow.",
                "Changes from my tablet take ages to appear on my phone.",
                "sync is sooo slow, sometimes {minutes} minutes before anything shows up",
                "The sync spinner just sits there doing nothing.",
                "I edited a list on my {computer} and the phone still had the old version an hour later.",
                "Sync between my iPad and phone lags badly.",
                "Waiting for sync every morning is getting old.",
                "Sync is so slow that I sometimes type the same note twice.",
                "My shopping list didn't sync until I was already out of the shop.",
                "It takes {minutes} minutes for a new note to sync to my {computer}.",
                "Syncing large notebooks crawls.",
                "~I added milk to the list on my laptop and my phone found out about it twenty minutes later.",
                "~sync 🐌🐌🐌",
                "~Love waiting ten minutes for my notes to show up on my phone. Really.",
            ],
            "pos": [
                "Sync is instant now, nice work on the fix.",
                "Notes appear on my other devices within seconds.",
                "Sync got so much faster in this version.",
                "The new sync is quick, my {computer} and phone are always in step.",
                "Finally sync just works and it's fast.",
                "~Sync isn't slow anymore, finally.",
                "~Edits on my laptop are on my phone before I've even picked it up.",
            ],
            "ticket_neg": [
                "Sync latency of several minutes between {computer} and {device}. Edits made on one device take "
                "{minutes}+ minutes to appear on the other. Version {version_seen}.",
                "Slow sync with large notebooks. A notebook with 2,000 notes takes over {minutes} minutes to "
                "sync after login. {version_seen}.",
            ],
        },
        "offline": {
            "name": "Offline mode",
            "description": "Using the app without a connection.",
            "neg": [
                "Offline mode won't open notes I haven't viewed recently.",
                "Without signal half my notebooks won't open.",
            ],
            "pos": [
                "Offline mode is a lifesaver on the subway.",
                "Works perfectly without signal.",
                "I can edit notes on the plane and nothing gets lost.",
                "Love that it works fully offline.",
                "Offline mode is the reason I switched from my old notes app.",
                "No wifi in my building's basement and the app still works great.",
                "Being able to use it offline when hiking is huge.",
                "It works offline, which none of the other apps I tried did properly.",
                "offline mode is perfect for my commute",
                "I travel a lot and the offline access is brilliant.",
                "Even in airplane mode all my lists are there.",
                "The offline support is rock solid.",
                "Great that I can write notes with zero bars of signal.",
                "Offline editing on my {device} is flawless.",
                "~Zero bars in the mountains and I still had every note.",
                "~Airplane mode doesn't bother it at all.",
            ],
            "ticket_neg": [
                "Notebooks unavailable offline. In airplane mode on {device}, notebooks not opened in the last "
                "week show an empty list. Version {version_seen}.",
            ],
        },
        "search": {
            "name": "Search",
            "description": "Finding notes by text.",
            "neg": [
                "Search can't find notes I know exist.",
                "Searching only matches titles, not the text inside notes.",
                "Search is slow once you have a lot of notes.",
                "Typing in the search box freezes the app for a second.",
                "Search results come back in a random order.",
                "search doesn't find words with accents",
                "I searched for a phone number I saved and got nothing.",
                "The search bar ignores tags.",
                "Search misses half of my notes.",
                "~I know I wrote down the wifi password somewhere but the app refuses to find it.",
                "~Search is not exactly reliable.",
            ],
            "pos": [
                "Search finds anything instantly.",
                "Love the search, it even finds words inside scanned receipts.",
                "Search is fast and accurate.",
            ],
            "ticket_neg": [
                "Full-text search misses note bodies. Searching for a word that only appears in the body of a "
                "note returns no results. {version_seen}, {device}.",
                "Search input lag. Each keystroke in search blocks the UI for about a second with 1,000+ notes.",
            ],
        },
        "reminders": {
            "name": "Reminders and notifications",
            "description": "Task reminders and their notifications.",
            "neg": [
                "Reminders stopped going off after the update.",
                "My reminder for {time} showed up three hours late.",
                "Notifications for due tasks never arrive anymore.",
                "Missed a meeting because the reminder didn't fire.",
                "Reminders are silent now even though notifications are on.",
                "Recurring reminders only work the first time.",
                "I set a reminder for {time} and got nothing.",
                "None of my reminders have gone off {since}.",
                "The reminder notification shows up after I've already opened the task.",
                "Reminders are completely broken on my {device}.",
                "Alerts for my to-dos stopped working.",
                "reminders worked fine before, now they just don't ring",
                "The daily reminder fires at random times now.",
                "Snoozed reminders never come back.",
                "~My 9am 'take meds' alert showed up at lunch.",
                "~Great, the to-do I set for my dentist appointment never pinged me.",
                "~remnders dont go off anymore",
            ],
            "pos": [
                "The reminders are reliable and easy to set.",
                "Love the location-based reminders.",
                "Reminders are the best part, they never miss.",
                "~Haven't missed a deadline since I started setting alerts in here.",
            ],
            "ticket_neg": [
                "Scheduled reminders not delivered on {version_seen}. Reminder set for {time} on {device}; no "
                "notification is shown. Notification permission is granted.",
                "Recurring reminder fires once, then never again. Steps: create a daily reminder, wait two days. "
                "{version_seen}.",
                "Reminder notifications delayed by hours. Seen on {device}, {version_seen}.",
            ],
        },
        "dark_mode": {
            "name": "Dark mode",
            "description": "The dark theme.",
            "neg": [
                "Dark mode still has white flashes when switching notes.",
                "Some text is unreadable in the dark theme.",
                "Dark mode resets to light every time I restart.",
            ],
            "pos": [
                "The dark theme is easy on the eyes.",
                "Finally a proper dark mode.",
                "Dark mode looks gorgeous on my {device}.",
            ],
        },
        "widgets": {
            "name": "Home-screen widgets",
            "description": "Widgets showing notes or tasks on the home screen.",
            "neg": [
                "The new widget doesn't update until I open the app.",
                "The widget shows a blank box on my home screen.",
                "Widget is stuck showing yesterday's tasks.",
            ],
            "pos": [
                "The new home screen widget is really handy.",
                "Love the to-do widget.",
            ],
            "ticket_neg": [
                "Widget not refreshing. Home-screen widget on {device} keeps showing stale tasks until the app is "
                "opened. {version_seen}.",
            ],
        },
        "pricing": {
            "name": "Pricing and subscription",
            "description": "Price, subscription and paywall.",
            "neg": [
                "$7 a month for a notes app is too much.",
                "They moved folders behind the paywall.",
                "The subscription price went up again.",
                "Too expensive compared to the free alternatives.",
                "Paying yearly and still getting upsell popups.",
                "~Seven bucks a month to write lists? No thanks.",
            ],
            "pos": [
                "Fair price for what you get.",
                "The lifetime licence was worth every penny.",
            ],
        },
        "editor": {
            "name": "Note editor",
            "description": "Writing and formatting notes and checklists.",
            "neg": [
                "Bullet points get messed up when I paste text.",
                "There's no way to change the font size in the editor.",
                "The cursor jumps to the end when I edit a long note.",
                "Formatting gets lost when I paste from email.",
            ],
            "pos": [
                "Markdown support is great.",
                "Checklists are so easy to make.",
                "The editor is clean and distraction free.",
                "I like that headings and bold just work.",
                "Drag to reorder checklist items is so satisfying.",
                "~Writing in it feels nice and clean.",
            ],
            "ticket_neg": [
                "Pasting rich text breaks bullet list formatting. Paste a bulleted list from an email into a note "
                "on {device}; bullets become plain text. {version_seen}.",
            ],
        },
        "export": {
            "name": "Export",
            "description": "Exporting notes to other formats.",
            "neg": [
                "Exporting to PDF loses all my images.",
                "Export to text mangles my checklists.",
            ],
            "req": [
                "Please add export to PDF.",
                "I wish I could export a whole folder at once.",
                "Would love a way to export everything to Markdown.",
            ],
            "ticket_req": [
                "Feature request: bulk export of a folder to Markdown or PDF.",
            ],
        },
        "stability": {
            "name": "Stability and crashes",
            "description": "Crashes and freezes.",
            "neg": [
                "It crashes when I open a long note.",
                "The app crashes on launch on my {device}.",
                "Crashes every time I rotate the screen.",
                "Froze and closed twice while I was typing.",
                "~It just closes itself when I open my big notes.",
            ],
            "ticket_neg": [
                "Crash when opening notes over 50 KB on {device}. Stack trace attached. {version_seen}.",
                "App crashes on rotation in the editor. {device}, {version_seen}.",
            ],
        },
        "sharing": {
            "name": "Sharing and collaboration",
            "description": "Sharing notes or lists with other people.",
            "pos": [
                "Sharing a grocery list with my partner works great.",
            ],
            "req": [
                "Please add a way to share lists with my family.",
                "It would be great to collaborate on a note with a coworker.",
                "Wish I could share a single checklist without sharing the whole folder.",
            ],
            "ticket_req": [
                "Feature request: shared lists that two accounts can edit.",
            ],
        },
    },
    "duplicates": [
        {
            "id": "darkmode-rant",
            "release": "2.2",
            "feature": "dark_mode",
            "polarity": "negative",
            "copies": [
                "THE NEW DARK MODE IS BLINDING!!! White panels everywhere, it's like staring into a lamp at "
                "midnight. Who tested this??? Fix it or I'm leaving.",
                "THE NEW DARK MODE IS BLINDING!!! White panels everywhere, it's like staring into a lamp at "
                "midnight. Who tested this??? Fix it or I'm leaving!!!",
                "the new dark mode is blinding!!! white panels everywhere, it's like staring into a lamp at "
                "midnight. who tested this??? fix it or i'm leaving.",
                "THE NEW DARK MODE IS BLINDING. White panels everywhere, it's like staring into a lamp at "
                "midnight. Who tested this? Fix it or I'm leaving.",
                "THE NEW DARK MODE IS BLINDING!!! White panels everywhere, it's like staring into a lamp at "
                "midnight. Who tested this??? Fix it or I'm leaving. ",
            ],
            "sources": ["app_store", "play_store", "issue_tracker", "app_store", "play_store"],
        },
    ],
    "noise_weights": {"generic_positive": 0.6, "generic_negative": 0.2, "off_topic": 0.15, "spam": 0.05},
    "noise": {
        "generic_positive": [
            "Great app!", "Love it, I use it every day.", "Five stars, does what it says.",
            "Best notes app I've tried.", "Does the job.", "Great app!", "Really good.",
            "Can't live without it now.", "Solid app, no complaints.", "Exactly what I needed.",
            "Very useful.", "Love it!!", "Brilliant little app.", "It's good. Recommended.",
        ],
        "generic_negative": [
            "Meh.", "Not for me.", "Used to be better.", "Disappointed.", "It's okay I guess.",
            "Not worth it.", "Expected more.",
        ],
        "off_topic": [
            "My dog stepped on my phone and wrote this review lol",
            "Wrong app, I meant to review my bank's app.",
            "first",
            "Testing testing 123",
            "Does anyone know if the shopping centre is open on Sundays?",
            "Happy birthday to my sister!",
            "Watching the football while writing this.",
        ],
        "spam": [
            "Follow my channel for daily productivity tips!! Link in bio",
            "Earn $500 a day from home, message me",
            "Check out my profile for free gift cards",
        ],
        "ticket_noise": [
            "Question: how do I move my account to a new email address?",
            "Duplicate of an earlier ticket, closing.",
            "Test ticket, please ignore.",
            "Wrong project, moving this ticket to the website tracker.",
        ],
    },
}
