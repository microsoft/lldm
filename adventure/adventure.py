import random
import requests
from requests import HTTPError
import json
import d20
import argparse
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


DEFAULT_ENDPOINT = "https://dasommer-oai-ncus.openai.azure.com/openai/deployments/gpt4o/chat/completions?api-version=2024-02-15-preview"
DEFAULT_ENDPOINT = "https://dasommer-oai-cmk.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview"
DEFAULT_KEY_VAULT = "aoaikeys"
DEFAULT_SN = "AOAIKey"
DEFAULT_SN = "AOAIKeySCUS"

api_key = ''
endpoint = ''
player = {}
player_text = ''

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
            }
        },
        "required": ["level", "slots"],
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
        "Class": {
            "type": "string"
        },
        "Level": {
            "type": "integer"
        },
        "Health": {
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
        "Magic": magic_schema
    },
    "required": ["Name", "Pronouns", "Class", "Level", "Health", "Abilities", "Proficiencies", "Magic"],
    "additionalProperties": False
}

# Combat schema.  Includes all information needed to manage combat
combat_schema = {
    "type": "object",
    "properties": {
        "in_combat": {
            "type": "boolean"
        },
        "surprise": {
            "type": "boolean"
        },
        "monster_AC": {
            "type": "integer"
        },
        "monster_attack_bonus": {
            "type": "integer"
        },
        "monster_health": {
            "type": "integer"
        },
        "monster_dexterity": {
            "type": "integer"
        },
        "monster_damage_dice": {
            "type": "string"
        }
    },
    "required": ["in_combat", "surprise", "monster_AC", "monster_attack_bonus", "monster_health", "monster_dexterity", "monster_damage_dice"],
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
        "health": {
            "type": "integer"
        },
        "gold": {
            "type": "integer"
        },
        "AC": {
            "type": "integer"
        },
        "inventory": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "spell_slots": spell_slots_schema,
        "spell_effects": {
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
        },
        "location": {
            "type": "string"
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
    "required": ["health", "gold", "AC", "inventory", "spell_slots", "spell_effects", "location", "time_of_day", "sunrise", "sunset", "date", "dark", "monsters", "NPCs"],
    "additionalProperties": False
}

game_schema = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string"
        },
        "game_state": game_state_schema,
    },
    "required": ["response", "game_state"],
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

def make_structured_request(system_prompt: str, user_prompt: str, second_system_prompt: str, schema: dict, max_tokens: int, conversation_context: list = [], temperature: float=0.7, top_p: float=0.95) -> dict:
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
    if response.status_code == 400:
        print(f"Error 400: Bad Request - {response.text}")
    response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code

    # Handle the response as needed (e.g., print or process)
    return response.json()['choices'][0]


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

After the user's turn, give a text response explaining in detail what happened.
'''

state_change_rules = '''
Examine the given action description and determine how the game state has changed, generating the new game state in JSON.  Only include the JSON response.
Game State includes the following:
Health is an integer value representing the player's hit points, according to D&D 5th Edition.
Gold is an integer that represents the number of gold pieces the player carries.  Do not let the player spend more gold then they have!
Inventory is a list of items that the player carries.  When the player picks up an item add it to the inventory.  When a player uses up an item or drop it then remove it from the inventory.
Time of Day tracks the current time of day, in HH:MM format using 24-hour time.  Actions take time and the time of day should be updated accordingly.
Sunrise and Sunset should be computed based on the current date.  These should also be used to determine when it is night.
Date tracks the current month and day and should be in a form like "July 1".  This is used to determine sunset and sunrise times as well as to determine seasons.
Dark determines if the player is operating in darkness, meaning the area is dark and the player has no light or night vision ability.
If any monsters are present in the room, they should each be listed.
Each monster should have an identifier which can be used to differentiate them from other monsters also present, typically constructed by adding an adjective to the monster type.
For example "Fierce Goblin" or "Sneaky Lizard".  Monsters should also have Health, a Description, AC, ability scores, and a status indicator.
The status indicator determines if the monster has some unusual status that might affect how it behaves in combat.
Any NPCs in the room should be listed in the NPC section.
NPCs have statistics very similar to those of a player character, and each NPC has a name.
'''

action_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
This game uses D&D 5th Edition rules.
The player is about to execute their turn and there may be other characters and monsters present who will act as well.
Using the supplied characer sheet, game state, and the rules of the game, determine all the actions that will occur during this turn, outputting everything in JSON and only JSON.
The first action will always be based on the command entered by the player.
This will be followed by actions from any monsters and NPCs present.
Finally any environmental actions will occur including sprung traps.
For each action, first determine if a die roll is necessary.
If a die roll is necessary, describe what rules
to use and how to determine whether this action will succeed or fail using the die roll, expressed as the dice to roll (in a form like "3d20") and a number to beat.
Dice to roll must only describe a dice expression and must not include extraneous text.  For example:  3d20+2 is OK.  3d20+Wisdom Modifier is wrong.
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

# Determine whether the next action will succeeed or fail, using the LLM to do most of the work
def llm_action_response(command: str, debug: bool) -> str:
    # Determine what die roll to make
    result = make_structured_request(action_rules + json.dumps(player, indent=4) + json.dumps(game_state, indent=4), command, None, round_schema, 5000, context)
    actions = json.loads(result['message']['content'])
    if debug:
        print(json.dumps(actions, indent=4))

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


def turn(command: str, debug: bool):
    global game_state
    global context

    # Determine success or failure of all actions on the upcoming turn
    success_message = llm_action_response(command, debug)

    # Perform the action
    if debug:
        print(success_message)
    result = make_structured_request(game_rules + json.dumps(player, indent=4) + json.dumps(game_state, indent=4), command, success_message, None, 5000, context)
    response = result['message']['content']
    print(response)
    new_state_response = make_structured_request(game_rules + '\n' + state_change_rules + '\nCurrent game state: ' + json.dumps(game_state, indent=4), response, None, game_state_schema, 5000, [])
    new_state = json.loads(new_state_response['message']['content'])
    context.append((command, response))
    game_state = new_state
    if debug:
        print(json.dumps(game_state, indent=4))
    if game_state['health'] <= 0:
        death_response = make_structured_request(death_rules + json.dumps(game_state, indent=4), '', None, None, 2000, context)
        print(death_response['message']['content'])
        exit(0)


def main():
    # Retrieve API Key from Keyvault
    global api_key
    global endpoint

    # Create the argument parser
    parser = argparse.ArgumentParser(description="Game World Setup")

    # Add arguments
    parser.add_argument('--scenario', type=str, required=True,
                        help='Path to the scenario file describing the world for the game.')
    parser.add_argument('--player', type=str, required=True,
                        help='Path to the player file describing attributes of the player.')
    parser.add_argument('--endpoint', type=str, default=DEFAULT_ENDPOINT,
                        help='URI to OAI or AOAI gpt4o endpoint.')
    parser.add_argument('--api_key', type=str, required=False,
                        help='API Key for (A)OAI endpoint (if not using keyvault)')
    parser.add_argument('--key_vault', type=str, default=DEFAULT_KEY_VAULT,
                        help='Name of the key vault to use to lookup the API Key')
    parser.add_argument('--secret_name', type=str, default=DEFAULT_SN,
                        help='Name of the secret in the key vault containing the API Key')
    parser.add_argument('--debug', type=bool, default=False, nargs='?',
                        const=True, help='Enable or disable debug mode (default: False).')

    # Parse arguments
    args = parser.parse_args()
    if not args.api_key:
        if not args.key_vault or not args.secret_name:
            print("Must specify either --api_key or both --key_vault and --secret_name")
            exit(1)
        api_key = get_api_key(args.key_vault, args.secret_name).value
    else:
        api_key = args.api_key
    endpoint = args.endpoint

    # Access the arguments
    scenario_file = args.scenario
    player_file = args.player
    debug_mode = args.debug

    read_player_file(player_file)
    if debug_mode:
        print(json.dumps(player, indent=4))
    read_scenario_file(scenario_file)
    if debug_mode:
        print(json.dumps(game_state, indent=4))

    turn('begin the game', debug_mode)
    while True:
        command = input('>')
        try:
            turn(command, debug_mode)
        except HTTPError as e:
            print(f'Turn failed with exception: {e}')

if __name__=="__main__":
    main()
