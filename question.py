import db
import json
from bottle import response, request
from mcOption import MCOption
from rubric import Rubric
from setup import Setup

class Question:
    def __init__(self, id, type, question_text, setup, points):
        '''Constructor'''
        self.id = id 
        self.type = type
        self.question_text = question_text
        self.setup = setup
        self.points = points



    def update(self):
        '''Commits changes to the database'''
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE QUESTION SET type = ?, question_text = ?, setup = ?, points = ? WHERE id = ?",
              (self.type, self.question_text, self.setup, self.points, self.id))
            conn.commit()

                
    def updateAns(self):
        ''' Commits changes to the Model Answer DB '''
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE MODEL_ANSWER SET answer_text = ? WHERE qid = ?",
                (self['answer_text'], self['qid']))
            conn.commit()
    @staticmethod
    def createFromJSON(data):
        if (data['type'] == "sql"):
            if(data['setup'] is None):
                abort(400, "SQL questions need an appropriate setup ID.")
        if (data['type'] != "mc"):
            if (data['answer'].isspace() or data["answer"] == "" or data['answer'] is None):
                abort(400, "SQL or SA questions need an appropriate answer.")
        if (data['question_text'].isspace() or data['question_text'] == ""):
            abort(400, "Invalid question text.")
        if (data['points'] < 0):
            abort(400, "Quetstion points must have a value greater than 0.")
        
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO QUESTION (type, question_text, setup, points) VALUES (?, ?, ?, ?)",                    
                (data['type'], data['question_text'], data['setup'], data['points']))
            conn.commit()
        qid = cursor.lastrowid

        if (data['type'] == 'sql' or data['type'] == 'sa'):
                cursor.execute("INSERT INTO Model_Answer (answer_text, qid) VALUES (?, ?)",                   
                    (data['answer'], qid))
                conn.commit()

        return Question.find(qid)

    ''' RETURN TO THIS AFTER FIND'''
    def updateFromJSON(self, data):
        if (self.type != data['type']):
            abort(400, "Cannot change the type of the question.")
        if (data['type'] == "sql"):
            if (data['setup'] is None):
                raise Exception("SQL Questions must have a valid setup.")
            else:
                self.setup = data['setup']
        if (self.type != "mc"):
            if (data['answer'].isspace() or data["answer"] == ""):
                raise Exception("Answer has to be valid.")
        if (data['question_text'].isspace() or data['question_text'] == ""):
            raise Exception("Invalid question text.")
        else:
            self.question_text = data['question_text']
        if (data['points'] > 0):
           self.points = data['points']
        else:
            abort(400, "Question points must have a value greater than 0.")

        Question.update(self)
        Question.updateAns({
            "qid": self.id,
            "answer_text": data['answer']
        })

    def jsonVer(self):
        mc_t = []
        mc_f = []
        ru_q = []
        with db.connect() as conn:
            c = conn.cursor()
            c.execute("""SELECT * FROM MCOption WHERE qid = ?""", (self.id,))

        #Gets the true and false options for the multiple choice table
        if (self.type == "mc"):
            for r in c:
                if (r['is_true'] == 1):
                    mc_t.append({
                        "id": r["id"],
                        "is_true": r["is_true"],
                        "option_text": r["option_text"],
                        "qid": r["qid"]
                    })
                else:
                    mc_f.append({
                        "id": r["id"],
                        "is_true": r["is_true"],
                        "option_text": r["option_text"],
                        "qid": r["qid"]
                    })
        #Gets the rubric options for the SA questions
        if self.type == "sa":
            c.execute("""SELECT * FROM Rubric WHERE qid = ?""", (self.id,))
            for r in c:
                ru_q.append({
                    "id": r["id"],
                    "rubric_text": r["rubric_text"],
                    "points": r["points"],
                    "qid": r["qid"]
                })
        if (self.type == "sa" or self.type == "sql"):
            c.execute("""SELECT * FROM Model_Answer WHERE qid = ?""", (self.id,))
            ans = c.fetchone()
        

        if (self.type == "mc"):
            return {
            "id": self.id,
            "type": self.type,
            "question_text": self.question_text,
            "points": self.points,
            "setup": self.setup,                
            "true_options": mc_t,
            "false_options": mc_f
         }
        if (self.type == "sa"):
            return {
                "id": self.id,
                "type": self.type,
                "question_text": self.question_text,
                "points": self.points,
                "setup": self.setup,                     
                "answer": ans['answer_text'],
                "rubrics": ru_q
            }
        if (self.type == "sql"):
            return {
                "id": self.id,
                "type": self.type,
                "question_text": self.question_text,
                "points": self.points,
                "setup": self.setup,                    
                "answer": ans['answer_text']
            }

    @staticmethod
    def find(id):
        with db.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM Question WHERE id = ?", (id,))
            q = c.fetchone()

        if (q is None):
            abort(404, f'A question with {id} does not exist')
        else:
            return Question(q['id'], q['type'], q['question_text'], q['setup'], q['points'])

                
    def delete(self):
        with db.connect() as conn:
            c = conn.cursor()
            c.execute("""DELETE FROM Model_Answer WHERE qid = ?""", (self.id,))
            if (self.type == "mc"):
                c.execute("""DELETE FROM MCOption WHERE qid = ?""", (self.id,))
            if (self.type == "sa"):
                c.execute("""DELETE FROM Rubric WHERE qid = ?""", (self.id,))
            c.execute("""DELETE FROM Question WHERE id = ?""", (self.id,))

   


    @staticmethod
    def setupBottleRoutes(app):
        @app.get('/question')
        def getQuestions():
            mcArr = []
            saArr = []
            sqlArr = []
            with db.connect() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM Question WHERE type = 'mc'")
                for r in c:
                    mcArr.append({
                        "id": r['id'],
                        "question_start": r['question_text'][0:40]
                    })
                c.execute("SELECT * FROM Question WHERE type = 'sa'")
                for r in c:
                    saArr.append({
                        "id": r['id'],
                        "question_start": r['question_text'][0:40]
                    })
                c.execute("SELECT * FROM Question WHERE type = 'sql'")
                for r in c:
                    sqlArr.append({
                        "id": r['id'],
                        "question_start": r['question_text'][0:40]
                    })
            response.content_type = 'application/json'
            return {
                "mc": mcArr,
                "sa": saArr,
                "sql": sqlArr
            }

        @app.get('/question/<qid>')
        def getQuestion(qid):
            try:
                q = Question.find(qid)
            except Exception:
                response.status = 404
                return f"Question not found."
            return q.jsonVer()
           

        @app.post('/question')
        def postQuestion():
            try:
                q = Question.createFromJSON(request.json)
            except Exception:
                response.status = 400
                return f"Your question was BAD."
            return q.jsonVer()

        @app.put('/question/<qid>')
        def putQuestion(qid):    
            try:  
                q = Question.find(qid)
            except Exception:
                response.status = 404
                return f"Question not found."
            try:
                q.updateFromJSON(request.json)
            except Exception:
                response.status = 400
                return f"There is an error with your submission"
            return q.jsonVer()
        @app.delete('/question/<qid>')
        def delQuestion(qid):
            try:
                q = Question.find(qid)
            except Exception:
                response.status = 404
                return f"That didn't exist, so I couldn't delete it."
            q.delete()
            response.content_type = 'application/json'
            return json.dumps(True)
    

            