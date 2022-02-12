import traceback

from actions import ActionHandler
from database import Database
from utils import print_msg_box

if __name__ == '__main__':
    db = Database()
    current_user = None

    action_handler = ActionHandler(current_user, db)
    while True:
        try:
            try:
                action_list = action_handler.action_list()
                description = 'Select an action\n\n    0 - Exit\n'
                for key, action in action_list.items():
                    description += f'    {key} - {action.description}\n'
                print_msg_box(description.strip(), indent=1, width=40)
                selected_action = int(input(">> "))
                if selected_action == 0:
                    break
                print('=' * 40)
                action_handler.run(action_list[selected_action])
            except KeyError:
                print(f"Action {selected_action} not found! please choose valid action.")
        except KeyboardInterrupt:
            print()
        except Exception as e:
            traceback.print_exc()
            break
        finally:
            print('=' * 40)
