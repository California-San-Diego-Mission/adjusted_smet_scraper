"""Mission specific functions."""

import time
import random
import holly
import padres


def process_message(msg: holly.ParsedHollyMessage):
    """Creates responses based on the message"""
    print(msg)

    if msg.match("who good human") or msg.match("who best human"):
        responses = ["The SMSLs", "ur mom", "Elder Coxson"]
        return random.choice(responses)

    if (msg.sender == "Norm Merritt" and random.randint(0, 4) == 3) or (msg.content[-2:] == ["Pres", "Merritt"] and len(msg.content) > 30):
        responses = ["yessir", "aye aye captain", "amen", "*salutes with paw*"]
        return random.choice(responses)

    if (msg.loose_match("did padres score") or msg.loose_match("homerun")):
        if padres.homerun(135, padres.get_yesterday_date()):
            return "yes! go get your free burger today. you're welcome"
        else:
            return "no, the padres did not get a homerun. very cringe."

    if msg.is_targeted() and msg.match("how should i find"):
        return "no"
    return None


def main():
    """Main function"""

    parser = holly.HollyParser()

    while True:
        try:
            client = holly.HollyClient()
            print('Connected to Holly')
            while True:
                raw_msg = client.recv()
                print(raw_msg)
                ret = process_message(raw_msg.parse(parser))
                if ret:
                    client.send(holly.HollyMessage(
                        content=ret, chat_id=raw_msg.chat_id, sender=''))

        except holly.HollyError as e:
            print(f"Error: {e}")

        print('Disconnected from Holly socket')
        time.sleep(30)


if __name__ == "__main__":
    main()
