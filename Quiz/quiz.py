import datetime
import sys
import random

class Quiz:
    def __init__(self):
        # define quiz properties
        self.name = ""
        self.description = ""
        self.questions = []
        self.score = 0
        self.correct_count = 0
        self.total_points = 0
        self.completion_time = 0

    def print_header(self):
        print("\n\n================================")
        print(f"QUIZ NAME: {self.name}")
        print(f"DESCRIPTION: {self.description}")
        print(f"QUESTIONS: {len(self.questions)}")
        print(f"TOTAL POINTS: {self.total_points}")
        print("================================\n")

    def print_results(self, quiztaker, thefile = sys.stdout):
        print("================================", file=thefile, flush=True)
        print(f"RESULTS for {quiztaker}", file=thefile, flush=True)
        print(f"Date: {datetime.datetime.today()}", file=thefile, flush=True)
        print(f"ELAPSED TIME: {self.completion_time}", file=thefile, flush=True)
        print(f"QUESTIONS: {self.correct_count} out of {len(self.questions)} correct.", file=thefile, flush=True)
        print(f"SCORE: {self.score} points out of possible {self.total_points}.", file=thefile, flush=True)
        print("================================\n", file=thefile, flush=True)

    def take_quiz(self):
        self.score = 0
        self.correct_count = 0
        self.completion_time = 0
        
        for q in self.questions:
            q.is_correct = False

        self.print_header()

        # randomize the questions
        random.shuffle(self.questions)

        # start time of quiz
        starttime = datetime.datetime.now()

        # Execute each question and record result
        for q in self.questions:
            q.ask()
            if (q.is_correct):
                self.correct_count += 1
                self.score += q.points
            print("================================\n")
        
        # end time of quiz
        endtime = datetime.datetime.now()

        if self.correct_count != len(self.questions):
            response = input("\nIt looks like you missed some questions. Re-do the wrong ones? (y/n)").lower()
            if response[0] == "y":
                wrong_qs = [q for q in self.questions if q.is_correct == False]
                # Execute each question and record result
                for q in wrong_qs:
                    q.ask()
                    if (q.is_correct):
                        self.correct_count += 1
                        self.score += q.points
                    print("================================\n")        
                # end time of quiz
                endtime = datetime.datetime.now()

        self.completion_time = endtime - starttime
        self.completion_time = datetime.timedelta(seconds = round(self.completion_time.total_seconds()))

        return (self.score, self.correct_count, self.total_points)

class Question:
    def __init__(self):
        self.points = 0
        self.correct_answer = ""
        self.text = ""
        self.is_correct = False

class QuestionTF(Question):
    def __init__(self):
        super().__init__()
    
    def ask(self):
        while (True):
            print(f"(T)rue or (F)alse: {self.text}")
            response = input("? ")

            if (len(response) == 0):
                print("Sorry, that's not a valid response. Please try again.")
                continue

            response = response.lower()
            if response[0] != "t" and response[0] != "f":
                print("Sorry, that's not a valid response. Please try again.")
                continue

            # Mark question as correct if answered correctly
            if response[0] == self.correct_answer:
                self.is_correct = True

            break

class QuestionMC(Question):
    def __init__(self):
        super().__init__()
        self.answers = []

    def ask(self):
        while (True):
            print(f"{self.text}")
            for a in self.answers:
                print(f"({a.name}) {a.text}")

            response = input("? ")

            if (len(response) == 0):
                print("Sorry, that's not a valid response. Please try again.")
                continue

            # Mark question as correct if answered correctly
            response = response.lower()
            if response[0] == self.correct_answer:
                self.is_correct = True
            
            break

class Answer:
    def __init__(self):
        self.text = ""
        self.name = ""