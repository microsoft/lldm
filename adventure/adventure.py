import requests
from requests import HTTPError
import json
import d20
import argparse
import datetime
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def get_api_key(key_vault_name, secret_name):
    # Set the key vault name and secret name
    key_vault_name = "aoaikeys"
    secret_name = "AOAIKey"
    secret_name = "AOAIKeySCUS"

    # Create the Key Vault URL
    key_vault_url = f"https://{key_vault_name}.vault.azure.net/"

    # Authenticate to Azure and get the secret
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    return client.get_secret(secret_name)


DEFAULT_ENDPOINT = "https://dasommer-oai-ncus.openai.azure.com/openai/deployments/gpt4o/chat/completions?api-version=2024-09-01-preview"
DEFAULT_ENDPOINT = "https://dasommer-oai-cmk.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-09-01-preview"
DEFAULT_KEY_VAULT = "aoaikeys"
DEFAULT_SN = "AOAIKey"
DEFAULT_SN = "AOAIKeySCUS"

api_key = ''
endpoint = ''
player = {}
player_text = ''
debug_mode = False

ability_schema = {
    "type": "object",
    "properties": {
        "Strength": {
            "type": "integer"
        },
        "Dexterity": {
            "type": "integer"
        },
        "Constitution": {
            "type": "integer"
        },
        "Intelligence": {
            "type": "integer"
        },
        "Wisdom": {
            "type": "integer"
        },
        "Charisma": {
            "type": "integer"
        }
    },
    "required": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"],
    "additionalProperties": False
}

# Magic schema, including spells known and spell slots
spell_slots_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "level": {
                "type": "integer"
            },
            "slots": {
                "type": "integer"
            },
            "max slots": {
                "type": "integer"
            }
        },
        "required": ["level", "slots", "max slots"],
        "additionalProperties": False
    }
}

magic_schema = {
    "type": "object",
    "properties": {
        "Spells Known": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "Cantrips Known": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "Spell Slots": spell_slots_schema
    },
    "required": ["Spells Known", "Cantrips Known", "Spell Slots"],
    "additionalProperties": False
}

spell_effects_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "effect": {
                "type": "string",
            },
            "minutes_remaining": {
                "type": "integer"
            }
        },
        "required": ["effect", "minutes_remaining"],
        "additionalProperties": False
    }
}

# Character schema.  This defines the player character and all abilities
character_schema = {
    "type": "object",
    "properties": {
        "Name": {
            "type": "string"
        },
        "Pronouns": {
            "type": "string"
        },
        "Race": {
            "type": "string"
        },
        "Class": {
            "type": "string"
        },
        "Level": {
            "type": "integer"
        },
        "XP": {
            "type": "integer"
        },
        "HP": {
            "type": "integer"
        },
        "Max HP": {
            "type": "integer"
        },
        "Status": {
            "type": "string"
        },
        "Gold": {
            "type": "integer"
        },
        "AC": {
            "type": "integer"
        },
        "Abilities": ability_schema,
        "Proficiencies": {
            "type": "object",
            "properties": {
                "Skills": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "Weapons": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "Saving Throws": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": ["Skills", "Weapons", "Saving Throws"],
            "additionalProperties": False
        },
        "Magic": magic_schema,
        "Spell Effects": spell_effects_schema,
        "Inventory": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["Name", "Pronouns", "Race", "Class", "Level", "XP", "HP", "Max HP", "Status", "Gold", "AC", "Abilities", "Proficiencies", "Magic", "Spell Effects", "Inventory"],
    "additionalProperties": False
}

monster_schema = {
    "type": "object",
    "properties": {
        "identifier": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "abilities": ability_schema,
        "AC": {
            "type": "integer"
        },
        "health": {
            "type": "integer"
        },
        "status": {
            "type": "string"
        }
    },
    "required": ["identifier", "description", "abilities", "AC", "health", "status"],
    "additionalProperties": False
}

# Define the game schema (JSON Schema).  This defines the structured state of the game.
game_state_schema = {
    "type": "object",
    "properties": {
        "player": character_schema,
        "location": {
            "type": "string"
        },
        "danger": {
            "type": "string",
            "enum": ["safe", "low", "medium", "high", "very high"]
        },
        "time_of_day": {
            "type": "string"
        },
        "sunrise": {
            "type": "string"
        },
        "sunset": {
            "type": "string"
        },
        "date": {
            "type": "string"
        },
        "dark": {
            "type": "boolean"
        },
        "monsters": {
            "type": "array",
            "items": monster_schema
        },
        "NPCs": {
            "type": "array",
            "items": character_schema
        }
    },
    "required": ["player", "location", "danger", "time_of_day", "sunrise", "sunset", "date", "dark", "monsters", "NPCs"],
    "additionalProperties": False
}

action_schema = {
    "type": "object",
    "properties": {
        "action_type": {
            "type": "string"
        },
        "how_to_resolve": {
            "type": "string"
        },
        "advantage": {
            "type": "boolean"
        },
        "disadvantage": {
            "type": "boolean"
        },
        "dice_to_roll": {
            "type": "string"
        },
        "number_to_beat": {
            "type": "integer"
        },
        "result_if_successful": {
            "type": "string"
        },
        "result_if_failed": {
            "type": "string"
        }
    },
    "required": ["action_type", "how_to_resolve", "advantage", "disadvantage", "dice_to_roll", "number_to_beat", "result_if_successful", "result_if_failed"],
    "additionalProperties": False
}

round_schema = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": action_schema
        }
    },
    "required": ["actions"],
    "additionalProperties": False
}

response_schema = {
    "type": "object",
    "properties": {
        "player_response": {
            "type": "string"
        },
        "DM_response": {
            "type": "string"
        }
    },
    "required": ["player_response", "DM_response"],
    "additionalProperties": False
}

def make_structured_request(system_prompt: str, user_prompt: str, second_system_prompt: str, schema: dict, max_tokens: int, conversation_context: list = [], temperature: float=0.7, top_p: float=0.95) -> dict:
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
        "Authorization": f"Bearer {api_key}"
    }

    # Payload for the request
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": system_prompt
                }
            ]
            }
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    }

    if schema:
        payload['response_format'] = {
            "type": "json_schema",
            "json_schema": {
                "name": "game_response",
                "schema": schema,
                "strict": True
            }
        }

    # Add conversation context
    for context_entry in conversation_context:
        payload['messages'].append({
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': context_entry[0]
                }
            ]
        })
        payload['messages'].append({
            'role': 'assistant',
            'content': [
                {
                    'type': 'text',
                    'text': context_entry[1]
                }
            ]
        })

    # Add a second system prompt if provided
    if second_system_prompt:
        payload['messages'].append({
            'role': 'system',
            'content': [
                {
                    'type': 'text',
                    'text': second_system_prompt
                }
            ]
        })

    # Finally the user's prompt
    payload['messages'].append({
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": user_prompt
            }
        ]
    })

    # Send request
    response = requests.post(endpoint, headers=headers, json=payload)
    if response.status_code >= 400:
        print(f"Error {response.status_code} - {response.text}")
    response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code

    # Handle the response as needed (e.g., print or process)
    return response.json()['choices'][0]


def make_self_play_request(system_prompt: str, user_prompt: str, conversation_context: list = [], max_tokens: int = 5000, temperature: float=0.7, top_p: float=0.95) -> str:
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    # Payload for the request
    payload = {
        "messages": [
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": system_prompt
                }
            ]
            }
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    }

    # Add conversation context
    for context_entry in conversation_context:
        payload['messages'].append({
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': context_entry[0]
                }
            ]
        })
        payload['messages'].append({
            'role': 'assistant',
            'content': [
                {
                    'type': 'text',
                    'text': context_entry[1]
                }
            ]
        })

    # Finally the user's prompt
    payload['messages'].append({
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": user_prompt
            }
        ]
    })

    # Send request
    print(json.dumps(payload, indent=4))
    response = requests.post(endpoint, headers=headers, json=payload)
    if response.status_code >= 400:
        print(f"Error {response.status_code} - {response.text}")
    response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code

    # Handle the response as needed (e.g., print or process)
    return response.json()['choices'][0]['message']['content']


# Apply the defined state change to the game state
def apply_state_change(state: dict, change: dict):
    state['gold'] += change['add_gold']
    new_inventory = []
    for item in state['inventory']:
        if item not in change['remove_inventory']:
            new_inventory.append(item)
    for item in change['add_inventory']:
        new_inventory.append(item)
    state['inventory'] = new_inventory
    if change['set_location']:
        state['location'] = change['set_location']


game_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
The user is a player in the game.  When the user types a request you are to return a text response explaining what happened and describing
where the player ends up.  You are to stay in character as the DM and not reveal any hidden information about the game world.
The player may move around by going in one of the four cardinal directions or by specifying a visible location.
The player may interact with objects and characters, enter combat, pick up and manipulate items, check their inventory, and check their health.
The player may ask basic questions about the game but you must only reveal what they know or can see.
The player may not spend more gold then they have.  If the player attempts to offer more gold than they have while bargaining, their offer will be rejected.

Light:
Some areas are dark, including unlit interior spaces along with anything outdoors if not near a light source.
When in a dark area the player will need light or they will be unable to see unless they have a natural ability to see in the dark.
Moving in the dark wihtout light or night vision is very dangerous.  Checks must be made on every movement and all player actions
will be taken with disadvantage.

Magic:
Magic follows the rules of D&D 5th Edition.
only spellcasters may cast magic spells or cantrips.
Spellcasters may only cast spells that they know.
A spellcaster may only cast a spell if they have a spell slot for that spell's level.
For example, a spellcaster must have a first level spell slot to cast the first level spell Magic Missile.
Casting a spell deducts a spell slot for that spell's level.
Spellcasters may freely cast any cantrips that they know.  Cantrips do not consume spell slots.
Spellcasters may not cast cantrips that they do not know.

Wandering Encounters:
Wandering monsters may appear whenever the player is in a dangerous area.  To perform a wandering encounter check, roll a d20.  The target value depends on how dangerous the area is:
low: 20
medium: 19
high: 18
very high: 17
While traveling outside on the road, check once every six hours.  The encounter may be friendly (travelers) or hostile (bandits, wild animals, roving goblins, etc).  Hostile encounters are more likely
if the player is far from a town or if the player is an area with known enemy activity.
In the wilderness off the main road, check once every hour.  Encounters are generally hostile with area-appropriate wild animals being more common.
In a "dungeon" area like a ruin or cave, check every hour and whenever the player enters a new area.  Encounters should be appropriate to the area.
If the player attempts to sleep in the wilderness or a dungeon that has not been cleared, always check for wandering encounters.  If an encounter occurs, the player's sleep will be interrupted.

Death:
If the player's health reaches zero, they will be knocked out.  Unless there is an NPC or ally nearby who can
help or unless somebody happens to find the player, they will die and the game will end.
If the player's health drops below zero, they will die immediately.
'''

response_rules = '''
After the user's turn, provide two responses in JSON format:
First, a description of what happened from the Player's point of view.  This should only include what the player can
see/perceive.  Do not include any game rule information here like die rolls or damage points.
Second, a description from the DM's perspective covering what happened to the player,
monsters, NPCs, and environment.  This should include all state changes and may include information that should be hidden
from the player and should be specific about damage points, time taken, etc.
'''

state_change_rules = '''
Examine the given action description and determine how the game state has changed, generating the new game state in JSON.  Only include the JSON response.

Player: this defines the player character and includes their current HP, according to D&D 5th Edition.  When the player takes damage, subtract the damage total from HP.  If HP reaches 0
or lower the player will die.
When the player is healed, increase HP but only up to the player's Max HP.

The Player object also tracks Gold: this is an integer value tracking the number of gold pieces the player carries.
When the player makes a purchase, subtract the purchase price from Gold.
When the player sells an item, add the sale price to Gold.
When the player finds money, add the amount to Gold.
Do not change Gold if the player is just bargaining or asking about prices.  The player must explicitly accept a deal or specify a purchase before Gold may change.

Inventory: this is a list of items that the player carries.
When the player picks up an item add it to the inventory.
If an NPC gives an item to the player, add it to the inventory.
When a player uses up an item or drop it then remove it from the inventory.
When the player makes a purchase, add the purchased item to the inventory.  Do not add an item if the player is just bargaining or browsing items.
When the player makes a sale, remove the sold item from the inventory.  Do not remove an item if the player is just bargaining.
The player must explicitly accept a deal or specify a purchase before Inventory may change.
Do not add the same item to the inventory more than once unless the player explicitly acquires multiple items.

Danger: the danger field determines how dangerous the current area is, expressed as safe, low, medium, high, or very high.

Examples:
"The player purchases the amulet for 10 gold pieces" -> subtract 10 from gold and add the amulet to inventory
"The merchant offers the amulet for 10 gold pieces" -> no change to gold or inventory.  This is just an offer that the player has not accepted.
"The player browses the shelves and notices a fine dagger.  The merchant quotes a price of 5 gold" --> No change to gold or inventory.
"The merchant accepts the player's offer of 10 gold pieces" -> subtract 10 from gold and add the item to inventory.  The offer was accepted.

Time of Day tracks the current time of day, in HH:MM format using 24-hour time.  Actions take time and the time of day should be updated accordingly.
Sunrise and Sunset should be computed based on the current date.  These should also be used to determine when it is night.
Date tracks the current month and day and should be in a form like "July 1".  This is used to determine sunset and sunrise times as well as to determine seasons.
Dark determines if the player is operating in darkness, meaning the area is dark and the player has no light or night vision ability.

Spell Effects track spells in effect that currently impact either the player or any NPCs or monsters.  Each spell effect has a remaining duration.
When time passes, deduct the minutes that pass from the duration of each spell effect.
If duration reaches or drops below 0, remove the spell effect.

If any monsters are present in the room, they should each be listed.
Each monster should have an identifier which can be used to differentiate them from other monsters also present, typically constructed by adding an adjective to the monster type.
For example "Fierce Goblin" or "Sneaky Lizard".  Monsters should also have Health, a Description, AC, ability scores, and a status indicator.
The status indicator determines if the monster has some unusual status that might affect how it behaves in combat.

Any NPCs in the room should be listed in the NPC section.
NPCs have statistics very similar to those of a player character, and each NPC has a name and pronouns.
'''

action_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
This game uses D&D 5th Edition rules.
The player is about to execute their turn and there may be other characters and monsters present who will act as well.
Using the supplied characer sheet, game state, and the rules of the game, determine all the actions that will occur during this turn, outputting everything in JSON and only JSON.
The first action will always be based on the command entered by the player.
This will be followed by actions from any monsters and NPCs present.
Next any environmental actions will occur including sprung traps.
Finally, if the player is not already in combat a wandering encounter check will be made if needed.
For each action, first determine if a die roll is necessary.
If a die roll is necessary, describe what rules
to use and how to determine whether this action will succeed or fail using the die roll, expressed as the dice to roll (in a form like "3d20") and a number to beat.
Dice to roll must only describe a dice expression and must not include extraneous text or names of modifiers.
Legal examples:  3d20 + 2, d20+4+1d4, 2d20+d6+2.  
Illegal examples: 3d20 + Wisdom Modifier, d20 + Charisma Modifier, 2d20 + Player Saving Throw
If a die roll is not necessary, leave dice_to_roll blank (empty string)
Set advantage if the die roll is to be made with Advantage
Set disadvantage if the die roll is to be made with Disadvantage
Also generate two descriptions: one that details what will happen if the action succeeds and another that details what will happen
if the action fails.  The descriptions should be in third-person, from the perspective of the Dungeon Master, and they should be in future tense.
These descriptions may optinoally include die rolls for damage or similar effect.
Examples of descriptions:
The player's longsword will strike the Goblin for 1d8 points of damage
The player will attempt to pick the lock but will fail
The Orc will miss the player on the next round
The player's attempt to search for treasure will trigger a poison needle trap

Darkness:
Moving around in darkness is extremely dangerous and will always require a check taken with disadvantage.
Other actions take in darkness are always done with disadvantage.

Game Commands:
The player may execute some actions that are designed to control the game itself.  These are treated specially:
The game has a debug mode, which if turned on results in extra messages being displayed.
If the player tries to turn on debug mode, create an action with action_type set to precisely debug_mode_on
If the player tries to turn off debug mode, create an action with action_type set to precisely debug_mode_off
If the player tries to save the game, create an action with action_type set to precisely save_game
If the player tries to load the game or restore the game, create an action with action_type set to precisely load_game
If the player tries to quit the game, create an action with action_type set to precisely quit_game
'''

death_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
The player has just died.  Display an appropriate game over message and summarize the player's achievements.
'''

character_rules = '''
What follows is a description of a character in a fantasy role-playing game using D&D 5th Edition rules.
Generate the character's statistics using a structured JSON format.
For spellcasters, magic spell slots should be determined using D&D 5th Edition rules based on the character class and level.
Spells known and cantrips known should be filled out as would be typical based on the character background.
'''

self_play_prompt = '''
You are a player in a game based on Dungeons and Dragons 5th Edition.  You will issue commands like
"Enter the town" or "Attack the goblin" or "Ask about the treasure" and the game will respond with
a description of what happens.  Your goal is to explore the environment, acquire the equipment you need,
and go on an adventure seeking fame and riches!  On the way you may have to talk with other characters,
fight monsters, disarm traps, and more.
'''

game_state = {}

character = {}

context = []

def read_player_file(player_file: str):
    global player
    global player_text

    file_content = None
    try:
        with open(player_file, 'r') as file:
            file_content = file.read()
    except FileNotFoundError:
        print(f"The player file at {player_file} was not found.")
        exit(0)
    
    player_response = make_structured_request(character_rules, file_content, None, character_schema, 2000, [])
    player = json.loads(player_response['message']['content'])
    player_text = file_content

def read_scenario_file(scenario_file: str):
    global context
    global game_state

    file_content = None
    try:
        with open(scenario_file, 'r') as file:
            file_content = file.read()
    except FileNotFoundError:
        print(f"The scenario file at {scenario_file} was not found.")
        exit(0)
    
    # Make an LLM call to determine the initial game state from the text in the scenario file
    initial_state_response = make_structured_request(state_change_rules + '\n' + json.dumps(player, indent=4), file_content + '\n' + player_text, None, game_state_schema, 5000, [])
    #initial_state_response = make_structured_request(state_change_rules + '\n' + json.dumps(player, indent=4), file_content + '\n' + player_text, None, None, 5000, [])
    game_state = json.loads(initial_state_response['message']['content'])
    context.append(('Game World', file_content))
    context.append(('Player', player_text))


# Roll dice, taking into account advantage and disadvantage 
def roll_dice(dice_to_roll: str, advantage: bool, disadvantage: bool) -> int:
    result = d20.roll(dice_to_roll).total
    if advantage:
        result2 = d20.roll(dice_to_roll).total
        if result2 > result:
            result = result2
    if disadvantage:
        result2 = d20.roll(dice_to_roll).total
        if result2 < result:
            result = result2
    return result


def generate_save_filename(character_name):
    # Convert the character name to lowercase and replace spaces with underscores
    formatted_name = character_name.lower().replace(" ", "_")
    
    # Get the current date and time
    now = datetime.datetime.now()
    
    # Format the date and time as YYYYMMDD_HHMMSS
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # Combine the formatted name and timestamp
    return f"{formatted_name}_{timestamp}.sav"

# Save the game by recording the player sheet, game state, and game context
def save_game(player: dict, game_state: dict, context: list) -> str:
    json_save = {
        'player': player,
        'game_state': game_state,
        'context': []
    }
    for context_entry in context:
        json_entry = {
            'player': context_entry[0],
            'game': context_entry[1]
        }
        json_save['context'].append(json_entry)
    filename = generate_save_filename(player['Name'])
    with open(filename, 'w') as f:
        json.dump(json_save, f, indent=4)

    return filename

def load_game(filename: str) -> str:
    global player
    global game_state
    global context

    saved_game = None
    with open(filename, 'r') as f:
        saved_game = json.load(f)
    player = saved_game['player']
    game_state = saved_game['game_state']
    context = []
    for context_entry in saved_game['context']:
        new_entry = (context_entry['player'], context_entry['game'])
        context.append(new_entry)

    print('Game loaded')
    print()
    print(context[-1][1])

    # Return the response we just sent to the player.
    return context[-1][1]

# Determine whether the next action will succeeed or fail, using the LLM to do most of the work
# Returns two values:
# message indicates the success message to append to the next prompt
# command will be set if the user's request was a special command (e.g. saving the game, turning debug mode on or off)
def llm_action_response(command: str, debug: bool):
    global debug_mode
    global player
    global game_state
    global context

    # Determine what die roll to make
    result = make_structured_request(action_rules + json.dumps(player, indent=4) + json.dumps(game_state, indent=4), command, None, round_schema, 5000, context)
    actions = json.loads(result['message']['content'])
    if debug:
        print(json.dumps(actions, indent=4))

    # Check for game commands and handle them here
    if len(actions) >= 1:
        command = actions['actions'][0]['action_type']
        if command == 'debug_mode_on':
            debug_mode = True
            print('Debug mode on')
            return None
        if command == 'debug_mode_off':
            debug_mode = False
            print('Debug mode off')
            return None
        if command == 'save_game':
            filename = save_game(player, game_state, context)
            print(f'Game saved to file {filename}')
            return None
        if command == 'quit_game':
            filename = save_game(player, game_state, context)
            print(f'Game saved to file {filename}')
            print('Thank you for playing!')
            exit(0)

    # Perform the die roll and see if we beat the target
    message = ''
    for action in actions['actions']:
        if action['dice_to_roll']:
            try:
                roll = roll_dice(action['dice_to_roll'], action['advantage'], action['disadvantage'])
                if roll >= action['number_to_beat']:
                    message += action['result_if_successful'] + "\n"
                else:
                    message += action['result_if_failed'] + "\n"
            except d20.errors.RollSyntaxError as e:
                # on the off chance we gat bad die roll syntax, show the error but don't halt the game; just omit the action message
                print(f'Die roll error: {e}')
    return message


def turn(command: str, debug: bool) -> str:
    global game_state
    global context

    # Determine success or failure of all actions on the upcoming turn
    success_message = llm_action_response(command, debug)
    if success_message is None:
        return 'Game command'

    # Perform the action
    if debug:
        print(success_message)
    result = make_structured_request(game_rules + '\n' + json.dumps(game_state, indent=4) + '\n' + response_rules, command, success_message, response_schema, 5000, context)
    full_response = json.loads(result['message']['content'])
    player_response = full_response['player_response']
    DM_response = full_response['DM_response']
    if debug:
        print(f'DM response: {DM_response}')
        print('\nPlayer response:')
    print(player_response)
    new_state_response = make_structured_request(game_rules + '\n' + state_change_rules + '\nCurrent game state: ' + json.dumps(game_state, indent=4), DM_response, None, game_state_schema, 5000, [])
    new_state = json.loads(new_state_response['message']['content'])
    context.append((command, player_response))
    game_state = new_state
    if debug:
        print(json.dumps(game_state, indent=4))
    '''
    if game_state['health'] <= 0:
        death_response = make_structured_request(death_rules + json.dumps(game_state, indent=4), '', None, None, 2000, context)
        print(death_response['message']['content'])
        exit(0)
    '''
    return player_response


def main():
    # Retrieve API Key from Keyvault
    global api_key
    global endpoint
    global debug_mode

    # Create the argument parser
    parser = argparse.ArgumentParser(description="Game World Setup")

    # Add arguments
    parser.add_argument('--scenario', type=str, required=False,
                        help='Path to the scenario file describing the world for the game.')
    parser.add_argument('--player', type=str, required=False,
                        help='Path to the player file describing attributes of the player.')
    parser.add_argument('--endpoint', type=str, default=DEFAULT_ENDPOINT,
                        help='URI to OAI or AOAI gpt4o endpoint.')
    parser.add_argument('--api_key', type=str, required=False,
                        help='API Key for (A)OAI endpoint (if not using keyvault)')
    parser.add_argument('--key_vault', type=str, default=DEFAULT_KEY_VAULT,
                        help='Name of the key vault to use to lookup the API Key')
    parser.add_argument('--secret_name', type=str, default=DEFAULT_SN,
                        help='Name of the secret in the key vault containing the API Key')
    parser.add_argument('--load_game', type=str, required=False,
                        help='Set this to a filename to restore a saved game.')
    parser.add_argument('--debug', type=bool, default=False, nargs='?',
                        const=True, help='Enable or disable debug mode (default: False).')
    parser.add_argument('--self_play', type=bool, default=False, nargs='?',
                        const=True, help='Enable or disable self-play mode (default: False).')

    # Parse arguments
    args = parser.parse_args()

    if not args.load_game:
        if not args.player or not args.scenario:
            parser.error("--player and --scenario are required if --load_game is not specified.")

    if not args.api_key:
        if not args.key_vault or not args.secret_name:
            parser.error("Must specify either --api_key or both --key_vault and --secret_name")
        api_key = get_api_key(args.key_vault, args.secret_name).value
    else:
        api_key = args.api_key
    endpoint = args.endpoint

    # Access the arguments
    scenario_file = args.scenario
    player_file = args.player
    debug_mode = args.debug
    self_play = args.self_play

    if player_file:
        read_player_file(player_file)
        if debug_mode:
            print(json.dumps(player, indent=4))
    if scenario_file:
        read_scenario_file(scenario_file)
        if debug_mode:
            print(json.dumps(game_state, indent=4))

    self_play_context = None

    if args.load_game:
        last_response = load_game(args.load_game)
    else:
        last_response = turn('begin the game', debug_mode)
    if self_play:
        self_play_context = []
    while True:
        if self_play:
            command = make_self_play_request(self_play_prompt, last_response, self_play_context)
            self_play_context.append((last_response, command))
            print(f'> {command}')
        else:
            command = input('>')
        try:
            last_response = turn(command, debug_mode)
        except HTTPError as e:
            print(f'Turn failed with exception: {e}')

if __name__=="__main__":
    main()
