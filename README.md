# How to set up and run the bot

"СГО" is a shorthand for "Сетевой город. Образование".

1. `git clone https://github.com/megahomyak/timetable_getter_bot`
2. Create `config.json` in `timetable_getter_bot/data` with the following contents:

       {
           "site_url": "FULL URL of your СГО's website",
           "vk_group_token": "Your VK group token",
           "vk_user_token": "Your VK user token (used to upload images to the group)",
           "sgo_username": "Your username in СГО",
           "sgo_password": "Your password in СГО",
           "school_name": "FULL NAME OF YOUR SCHOOL, as stated in the drop-down list in the login form of СГО",
           "timetable_checking_delay_in_seconds": 60,
           "minimum_timetable_sending_hour": 9,
           "maximum_timetable_sending_hour": 22,
           "timetable_weekdays": [0, 1, 2, 3, 4, 5],
           "do_logging": set to true if you want to see some of the bot's actions logged to the console (otherwise set to false),
           "print_incoming_messages": set to true if you want to see peer ids of incoming messages (otherwise set to false),
           "broadcast_peer_ids": [list of VK peer ids to send timetables to]
       }

   I think, fields without descriptions are self-explanatory.
3. Install the dependencies using poetry: `poetry install`
4. Run the bot in a poetry virtual environment: `poetry run python run.py`
