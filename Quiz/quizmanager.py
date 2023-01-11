# QuizManager manages the quiz content
import os.path
import os
import quizparser
import datetime

class QuizManager:
    def __init__(self, quizfolder):
        self.quizfolder = quizfolder
        # recently selected quiz
        self.the_quiz = None
        # collection of quizzes
        self.quizzes = dict()
        # store results of recent quiz
        self.results = None
        # name of the person taking the quiz
        self.quiztaker = ""

        if (os.path.exists(quizfolder) == False):
            raise FileNotFoundError("The quiz folder does not exists.")

        # Build the list of quizzes
        self._build_quiz_list()
    
    def _build_quiz_list(self):
        dircontents = os.scandir(self.quizfolder)

        for i, f in enumerate(dircontents):
            if f.is_file():
                parser = quizparser.QuizParser()
                self.quizzes[i+1] = parser.parse_quiz(f)

    # Print list of quizzes
    def list_quizzes(self):
        for k, v in self.quizzes.items():
            print(f"({k}): {v.name}")

    # Start quiz for the user and return the results
    def take_quiz(self, quizid, username):
        self.quiztaker = username
        self.the_quiz = self.quizzes[quizid]
        self.results = self.the_quiz.take_quiz()
        return (self.results)
    
    # Print the results of the most recently taken quiz
    def print_results(self):
        self.the_quiz.print_results(self.quiztaker)

    # Save the results of the most recent quiz to a file
    # The file is named using the current date as
    # QuizResults_YYYY_MM_DD_N (N is incremented until unique)
    def save_results(self):
        today = datetime.datetime.now()
        filename = f"QuizResults_{today.year}_{today.month}_{today.day}.txt"

        n = 1
        while(os.path.exists(filename)):
            filename = f"QuizResults_{today.year}_{today.month}_{today.day}_{n}.txt"
            n = n + 1
        
        with open(filename, "w") as f:
            self.the_quiz.print_results(self.quiztaker, f)

# Used for quick testing of this file.
if __name__ == "__main__":
    qm = QuizManager("Quizzes")
    qm.list_quizzes()