import os
from quizmanager import QuizManager

class QuizApp:
    QUIZ_FOLDER = "Quizzes"
    def __init__(self):
        self.username = ""
        self.qm = QuizManager(QuizApp.QUIZ_FOLDER)

    def startup(self):
        #print the greeting at startup
        self.greeting()

        self.username = input("What is your name? ")
        print(f"Welcome, {self.username}!")
        print()

    def greeting(self):
        print("================================")
        print("====== Welcome to PyQuiz! ======")
        print("================================")
        print()

    def menu_header(self):
        print("================================")
        print("Please make a selection:")
        print("(M): Repeat this menu.")
        print("(L): List quizzes.")
        print("(T): Take a quiz.")
        print("(E): Exit program.")
        print("================================")
        print()

    def menu_error(self):
        print("That's not a valid selection.  Please try again.")

    def goodbye(self):
        print("================================")
        print(f"Thanks for using PyQuiz, {self.username}!")
        print("================================")

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def menu(self):
        self.menu_header()
        #run until the user exists the app
        selection = ""
        while (True):            
            selection = input("Selection? (M) | (L) | (T) | (E) ")

            if len(selection) == 0:
                self.menu_error()
                continue
            
            selection = selection.capitalize()

            if selection[0] == 'E':
                self.goodbye()
                break
            elif selection[0] == 'M':
                self.menu_header()
                continue
            elif selection[0] == 'L':
                print("\nAvailable Quizzes Are: ")
                self.qm.list_quizzes()
                print("================================")
                print()
                continue
            elif selection[0] == 'T':
                try:
                    quiznum = int(input("Quiz number: "))
                    print(f"You have selected quiz {quiznum}")

                    # start the quiz
                    self.result = self.qm.take_quiz(quiznum, self.username)
                    self.qm.print_results()

                    dosave = input("Save the results? (y/n)")                    
                    dosave = dosave.capitalize()
                    if len(dosave) > 0 and dosave[0] == 'Y':
                        self.qm.save_results()      
                except:
                    self.menu_error()
            else:
                self.menu_error()
            
    # This is the entry point to the program
    def run(self):
        # Execute the startup routine - ask for name, print greeting, etc.
        self.startup()
        # Start the main program menu and run until the user exists.
        self.menu()

if __name__ == "__main__":
    app = QuizApp()
    app.run()
