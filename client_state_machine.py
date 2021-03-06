from chat_utils import *
import json
import secrets ### like random module but more secure ###


class ClientSM:
    def __init__(self, s):
        self.state = S_OFFLINE
        self.peer = ''
        self.me = ''
        self.out_msg = ''
        self.s = s
        ### Diffie-Hellman Key Exchange ###
        # user will be given a private key when login
        self.private_key = secrets.randbits(17)
        # base key for exponential; must be primitive root of clock key
        self.base_key = 17837
        # clock key for modulo; must be prime
        self.clock_key = 17977  # partition prime
        # final shared key!! first set to None
        self.shared_key = None

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    def connect_to(self, peer):
        ### IF REQUEST DECLINED, response["status"]=="busy"? ###
        msg = json.dumps({"action": "connect", "target": peer})
        mysend(self.s, msg)
        response = json.loads(myrecv(self.s))
        if response["status"] == "success":
            self.peer = peer
            self.out_msg += 'You are connected with ' + self.peer + '\n'
            return (True)
        elif response["status"] == "busy":
            self.out_msg += 'User is busy. Please try again later\n'
        elif response["status"] == "self":
            self.out_msg += 'Cannot talk to yourself (sick)\n'
        else:
            self.out_msg += 'User is not online, try again later\n'
        return(False)

    def disconnect(self):
        msg = json.dumps({"action": "disconnect"})
        mysend(self.s, msg)
        self.out_msg += 'You are disconnected from ' + self.peer + '\n'
        self.peer = ''
    
    ### producing keys with Diffie-Hellman Key Exchange method ###
    def produce_public_private_key(self):
        return self.base_key**self.private_key % self.clock_key

    def produce_shared_key(self, public_private_key):
        self.shared_key = public_private_key**self.private_key % self.clock_key
        return self.shared_key

    ### messages are encrypted and decrypted with Diffie-Hellman Key Exchange method ###
    def encrypt(self, msg):
        encrypted_msg = ""
        for digit in msg:
            encrypted_msg += chr(ord(digit)+self.shared_key)
        return encrypted_msg

    def decrypt(self, encrypted_msg):
        decrypted_msg = ""
        for digit in encrypted_msg:
            decrypted_msg += chr(ord(digit)-self.shared_key)
        return decrypted_msg

    def proc(self, my_msg, peer_msg):
        self.out_msg = ''
# ==============================================================================
# Once logged in, do a few things: get peer listing, connect, search
# And, of course, if you are so bored, just go
# This is event handling instate "S_LOGGEDIN"
# ==============================================================================
        if self.state == S_LOGGEDIN:
            # todo: can't deal with multiple lines yet
            if len(my_msg) > 0:

                if my_msg == 'q':
                    self.out_msg += 'See you next time!\n'
                    self.state = S_OFFLINE

                elif my_msg == 'time':
                    mysend(self.s, json.dumps({"action": "time"}))
                    time_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "Time is: " + time_in

                elif my_msg == 'who':
                    mysend(self.s, json.dumps({"action": "list"}))
                    logged_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += 'Here are all the users in the system:\n'
                    self.out_msg += logged_in

                elif my_msg[0] == 'c':
                    ### IF REQUEST DECLINED, self.state = S_LOGGEDIN ? ###
                    peer = my_msg[1:]
                    peer = peer.strip()
                    if self.connect_to(peer) == True:
                        self.state = S_CHATTING
                        self.out_msg += 'Connect to ' + peer + '. Chat away!\n\n'
                        self.out_msg += '-----------------------------------\n'
                        ### send public_private_key to peer thorugh server to create shared_key ###
                        ppkey = self.produce_public_private_key()
                        mysend(self.s, json.dumps({"action": "produce_public_private_keys", "target": self.peer, "message": ppkey}))
                    else:
                        self.out_msg += 'Connection unsuccessful\n'

                elif my_msg[0] == '?':
                    term = my_msg[1:].strip()
                    mysend(self.s, json.dumps(
                        {"action": "search", "target": term}))
                    search_rslt = json.loads(myrecv(self.s))["results"].strip()
                    if (len(search_rslt)) > 0:
                        self.out_msg += search_rslt + '\n\n'
                    else:
                        self.out_msg += '\'' + term + '\'' + ' not found\n\n'

                elif my_msg[0] == 'p' and my_msg[1:].isdigit():
                    poem_idx = my_msg[1:].strip()
                    mysend(self.s, json.dumps(
                        {"action": "poem", "target": poem_idx}))
                    poem = json.loads(myrecv(self.s))["results"]
                    if (len(poem) > 0):
                        self.out_msg += poem + '\n\n'
                    else:
                        self.out_msg += 'Sonnet ' + poem_idx + ' not found\n\n'

                else:
                    self.out_msg += menu

            if len(peer_msg) > 0:
                try:
                    peer_msg = json.loads(peer_msg)
                except Exception as err:
                    self.out_msg += " json.loads failed " + str(err)
                    return self.out_msg

                if peer_msg["action"] == "connect":
                    # ----------your code here------#
                    print(peer_msg)

                    self.peer = peer_msg["from"]
                    self.out_msg += f'''You've got a request from {self.peer}
                    You are now connected with {self.peer}. Start chatting!
                    --------------------------------------------------------'''
                    self.state = S_CHATTING
                    # ----------end of your code----#

# ==============================================================================
# Start chatting, 'bye' for quit
# This is event handling instate "S_CHATTING"
# ==============================================================================
        elif self.state == S_CHATTING:
            if len(my_msg) > 0:     # my stuff going out
                
                if my_msg == 'bye':
                    self.disconnect()
                    self.state = S_LOGGEDIN
                    self.peer = ''
                    
                ### encrypt self message ###
                encrypted_msg = self.encrypt(my_msg)
                mysend(self.s, json.dumps(
                    {"action": "exchange", "from": "[" + self.me + "]", "message": encrypted_msg}))
                    
                    
            if len(peer_msg) > 0:

                # ----------your code here------#
                peer_msg = json.loads(peer_msg)
                
                if peer_msg["action"] == "connect":
                    self.peer = peer_msg["from"]
                    self.out_msg += f'{peer_msg["from"]} joined the chat\n'
                    self.state = S_CHATTING
                
                ### send self's public_private_key to produce shared_key for peer ###
                elif peer_msg["action"] == "produce_public_private_keys":
                    ppkey = self.produce_public_private_key()
                    mysend(self.s, json.dumps(
                        {"action": "produce_shared_keys", "target": self.peer, "message": ppkey}))
                    self.public_private_key = int(peer_msg["message"])
                    self.shared_key = self.produce_shared_key(
                        self.public_private_key)
                    print(f"Your messages are encrypted. Chat away!")

                ### get peer's public_private_key to produce shared_key for self ###
                elif peer_msg["action"] == "produce_shared_keys":
                    self.public_private_key = int(peer_msg["message"])
                    self.shared_key = self.produce_shared_key(
                        self.public_private_key)
                    print(f"Your messages are encrypted. Chat away!")

                elif peer_msg["action"] == "exchange":
                    ### decrypt peer message ####
                    decrypted_msg = self.decrypt(peer_msg["message"])
                    self.out_msg += peer_msg["from"] + decrypted_msg
                
                elif peer_msg["action"] == "disconnect":
                    self.out_msg += f'{peer_msg["msg"]}\n'
                    self.state = S_LOGGEDIN
                

                # ----------end of your code----#
                
            # Display the menu again
            if self.state == S_LOGGEDIN:
                self.out_msg += menu
# ==============================================================================
# invalid state
# ==============================================================================
        else:
            self.out_msg += 'How did you wind up here??\n'
            print_state(self.state)

        return self.out_msg
