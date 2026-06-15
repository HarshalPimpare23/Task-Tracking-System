import os
import json
class Jsonopr():
    def redjson(self,filename):
        with open(filename,"r") as rf:
            data=json.load(rf)
        return data

    def updatejson(self,filename,data):
        with open(filename,"w") as wf:
            json.dump(data,wf,indent=4)
        return True

    # def login(self,login ):
    #         self.hide()
    #         self.window = login()
    #         self.window.show()

        

        

        

            