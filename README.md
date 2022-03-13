# How to set up and run the bot

1. `git clone https://github.com/megahomyak/timetable_getter_bot`
2. Create `config.json` in `timetable_getter_bot/data` with the following contents:

       {
           "site_url": "FULL URL of your 'Сетевой город's site",
           "vk_group_token": "Your VK group token",
           "vk_user_token": "Your VK user token (used to upload images to a group)",
           "sgo_username": "Your username in 'Сетевой город'",
           "sgo_password": "Your password in 'Сетевой город'",
           "school_name": "FULL NAME OF YOUR SCHOOL, as stated in the drop-down list in the login form of 'Сетевой город'",
           "timetable_checking_delay_in_seconds": 60,
           "minimum_timetable_sending_hour": 9,
           "maximum_timetable_sending_hour": 22,
           "timetable_weekdays": [0, 1, 2, 3, 4, 5],
           "do_logging": set to true if you want to see some of bot's actions logged to the console, otherwise set to false,
           "print_incoming_messages": set to true if you want to see peer ids of incoming messages, otherwise set to false,
           "broadcast_peer_ids": [list of VK peer ids]
       }

   I think, fields without descriptions are self-explanatory.
3. Run the script (entry point is `run.py` from the project root)