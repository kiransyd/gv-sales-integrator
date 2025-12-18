import requests
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# Load BASE_URL and READAI_SHARED_SECRET from .env
def load_env_var(key: str, default: str = "") -> str:
    """Load environment variable from .env file or environment"""
    # First check environment
    if key in os.environ:
        return os.environ[key]
    
    # Then check .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    
    return default

# Get webhook URL from .env
base_url = load_env_var("BASE_URL", "http://localhost:8000")
webhook_url = f"{base_url.rstrip('/')}/webhooks/readai"

# Get shared secret (optional)
readai_secret = load_env_var("READAI_SHARED_SECRET", "")

print(f"📤 Sending Read.ai webhook to: {webhook_url}")
if readai_secret:
    print(f"🔐 Using shared secret authentication")
else:
    print(f"⚠️  No READAI_SHARED_SECRET set (webhook will accept without auth)")
print()


# Parse transcript text
transcript_text = """[CPG] - Nissin Foods USA - Demo 
Thu, Oct 30, 2025

0:53 - CBollinger
Hi Chelsea. How are you?

0:56 - CBollinger
How are you? So I have Sara on the line. She is my colleague on the cup noodle side of the business.

1:09 - Unidentified Speaker
Hi, Sara. Nice to meet you.

1:10 - Unidentified Speaker
Hi, nice to meet you.

1:14 - Conference Room (Team GoVisually) - Speaker 1
I love all your backgrounds. I love the branding. I wish ours was more cooler.

1:24 - Sara R.
That was our designer got excited I just started making really fun ones.

1:31 - Unidentified Speaker
Love it.

1:32 - CBollinger
Which I don't have any because it's hard to upload on Zoom. And Sara is much more proactive than I.

1:41 - Sara R.
It's mostly just because I always have laundry hanging behind me. And so I have to have an option on Zoom. So I think this is the only one I have loaded because there's always, I have bikes behind me, laundry. So it would be very distracting if you could actually see what's behind me.

2:02 - Conference Room (Team GoVisually) - Speaker 1
Makes sense. We've all been there.

2:07 - CBollinger
So Wes messaged me and said that he might be a little bit late. And then I invited a couple other colleagues from my Team that didn't accept or declined the invitation. So their calendars look free, but I never know. So I think we can get started because truly Sara and I are the people that work on this the most. And then so I think it's really like we have the most insight and this will benefit us the most. I wanted to get Sara's kind of thoughts and buy in first.

2:50 - Conference Room (Team GoVisually) - Speaker 1
Well, thank you for sharing the Proof here. I think we had an issue with it being flattened. So what I'm going to is I'm going to use another one I have as a sample, but that's okay. We'll walk through. I think anyway.

3:10 - CBollinger
Okay, cool. And I saw the note, but I don't think we have what you need because we never get the AI file until the very end, like the delivery. So sorry.

3:21 - Conference Room (Team GoVisually) - Speaker 1
Yeah, no, that's not a problem. So what you'll notice is that, um, as part of the, as part of the workflow, the designers will get hooked into the system. So when the plugin uploads it, it'll automatically convert it into the correct format for GoVisually. So that's not a problem at all.

3:39 - Conference Room (Team GoVisually) - Speaker 1
So, yeah.

3:40 - CBollinger
That's amazing. And do you want to just give Sara like a quick overview of GoVisually? I know I've, I've told her like, it's a system that'll help us with routing, but in, in your words probably is a better, overview for her.

3:52 - Conference Room (Team GoVisually) - Speaker 1
Yes, thank you. Yeah, Sara, so what GoVisually is, we help essentially packaging creative teams and teams like yours accelerate your label to market. And the way we do that is to bring everyone on the same page at the same time and make sure you've got, you know, we capture all the feedback, all in a centralized place. We capture all the approvals in a centralized place so everyone knows where everything's up to. And we allow you to sort of move through that process. And another new thing we've been doing now is we've added a whole bunch of AI functionality, which essentially takes things that are highly time consuming. And turn that into which I'm going to show you today, which we turn that into a series of AI checks. So if you have like a lot of checklists internally, you've got to go through, or, you know, the FDA rules are changing, we keep all those database updated, and we flag immediately on the artwork, what may be compliant or non compliant. So you're always up to date. It'll also pick up things like formatting, you know, you may have some requirements, claims, doing branding checks, and all that type of thing. So that's a quick summary.

5:13 - Sara R.
I am intrigued by that last point. And you We'll probably get into this, but I'm just going to ask the question now anyway. Chelsea, don't tell anyone. Actually, I told Eamon. But I've been using AI, sorry, to help me check packaging and to look at changes from the last one to understand what's changed. And it's sort of hit or miss how well it works. I'm assuming your tool can also help us do that. So the biggest thing that is super time consuming is rereading an FNIL statement. Nutrition packs and ingredients list statements. And also, I think those have the highest risk for human error, because once we've looked at the same package six times, my brain starts to speed past all of it.

5:57 - Conference Room (Team GoVisually) - Speaker 1
Yeah, exactly.

5:59 - Conference Room (Team GoVisually) - Speaker 1
So let me take you through that. We have two ways of doing it. One is through a visual checkup, and we provide multiple ways of checking that. And then let dive into it and then you can, you can stop me and go, Hey, how does that work?

6:15 - CBollinger
Can you just give me a history, like super quick of like, how did you decide to do this? Like, where did this idea come from Cause I'm just so struck at how unique it is. And like where, how did GoVisually come about?

6:31 - Conference Room (Team GoVisually) - Speaker 1
So that's a great question. So many, many years ago, me and my co-founders, we ran an agency, So, and this was basically a side gig for us. So we've all had full-time jobs, but we were sort of like creative people. We liked, loved building things. I've always loved building stuff from the time I was like, I think nine years old. I just loved building things. So we used to run an agency on the side. And what we found was we were doing like a lot of creative work and people would be like emailing back and forth saying, can you change this? Can you change that? And we found that really frustrating. We don't quite really know what they meant. So we're like, there's got to be a better way of doing this. So that's how GoVisually, the very first version started. And once we took it to market, we found typically it was like agencies that were using it. Then we grew to like in-house marketing teams and branding teams. And then as we sort of stayed in the market long enough, we realized we were attracting the attention of a lot of companies like yourself, like doing internal, like, you know, the CPG market was growing, private labels were growing. And again, people were being frustrated with that. So about two, three years ago, we were, we realized that, hey, we can solve a lot of these through AI as AI was emerging. So we thought, how can we solve this to get people like, we realized like one of the biggest bottleneck is around compliance and doing all those little, you know, fiddly checks that was frustrating customers. So we thought, how can we evolve the platform into being a little bit more, you know, a little bit more focused on the CPG customers. And so, and here we are. So that's how we ended up here. So that's it.

8:16 - CBollinger
I was driving home last night and I was like, cause I'm just so excited for this, this program. Cause I think it'll really help us out time-wise. But I was like, how do you figure this out? Like, so very cool. Very cool.

8:28 - Conference Room (Team GoVisually) - Speaker 1
I just, I think it's just figuring it out because we're talking to a lot of people and once you understand, you start seeing patterns, everyone's having the same issues, right? And we're like, I think we can solve this. Well, thank you for joining. Let me start with my, what time is it for you at the moment? I don't feel so bad.

8:52 - Sara R.
What time is it for you?

8:55 - Conference Room (Team GoVisually) - Speaker 1
It's 8.40 AM. Yeah, not too bad. Are you in California as well, Sara?

9:02 - Sara R.
Yeah, we work out of the same office, yeah.

9:04 - Conference Room (Team GoVisually) - Speaker 1
The same office, okay. Where did you mention your office was again?

9:09 - Sara R.
It's LA area, I don't know how well you know LA.

9:13 - Conference Room (Team GoVisually) - Speaker 1
Only as a tourist.

9:15 - Sara R.
Then you're not going to know where we are.

9:17 - CBollinger
Beautiful Gardena, home of many auto shops and warehouses.

9:23 - Sara R.
Yeah, it's one of the more depressing places.

9:26 - Conference Room (Team GoVisually) - Speaker 1
lots of industry but fairly depressing you would never go as a tourist but if it helps we're like 15 minutes south of lax ish 15 20 minutes okay yeah yeah lax i've been through it many many times actually yeah all right let me open my screen and let's get started I want to make sure I open the right screen. I'll just share my entire desktop. I think it'll make it easier. Yeah, there we go. I'll just share my entire desktop. Let me know if you can see my screen and my mouse moving. Okay, great. Okay, so what you're seeing here is GoVisually, essentially. So the way we organize GoVisually is on the left, left, you will see all your projects and up here at the top, you will see the different stages, each Proof set. So you've got all the different proofs that have been organized into and this is my demo accounts. It's a kind of a little bit messy, but you can see here we support all types of files from, you know, PDFs, AI, Photoshop, even videos. So if you're ever going to be doing within your marketing Team, any videos or social content, we also support videos. Which I'll show you in a minute. So up here is your different stages the artwork's at. And along here you can also see all the different Team members that are involved in this particular project. So you can choose to include or remove anyone that doesn't need to be involved in a particular project, right? Straightforward so far. You also have the option of adding reviewers. So reviewers are folks who may come in and add a comment comment, but don't have any rights to like upload new versions or make any changes to the actual artwork. So this could be just someone who needs to even externally come and Review. So if you've got a lawyer who's involved in a process, you can just add them as an external reviewer. So they'll get a link or they'll have access to their own portal where as you upload new revisions, they'll just be able to. It looks like someone's joined. Ayaka has joined. Ah, yes, Ayaka.

11:47 - CBollinger
She's our other teammate.

11:49 - Conference Room (Team GoVisually) - Speaker 1
OK, awesome. Did you want me to start again or continue from where I am?

11:56 - CBollinger
You can continue.

11:57 - Conference Room (Team GoVisually) - Speaker 1
Hi, Ayaka. Not sure if she can hear me.

12:05 - Sara R.
I was going to ask, the external thing's really interesting. You don't. It sounds like you don't have to be embedded in the program to use it, though. For example, we use an external regulatory agency. They would just get a link to be able to Review it, is what you're saying, and they don't need to be signed up.

12:26 - Conference Room (Team GoVisually) - Speaker 1
No, they don't need to be signed up. Hi, Ayaka. Thank you for joining.

12:31 - Ayaka Morimoto
Sorry for the delay. That's all right.

12:33 - Unidentified Speaker
No worries.

12:34 - Unidentified Speaker
I'm back now.

12:36 - Conference Room (Team GoVisually) - Speaker 1
No problems. Thank you for joining. Yeah, that's right. So reviewers will just get like a link and they'll only so you can share it in some different ways. So, for example, you may only want to individually share particular artworks. For example, this one, you can just go in and say click on share. So they would only ever see that one single artwork. You can share an entire section. So, for example, here you can create a section called legal approvals and share that entire section. So they would see all the artwork in that particular section, or you can click on the share button here and they will see everything, right? So different people can have different views on what they actually get to see.

13:17 - Sara R.
And then this is really nuanced, but just wondering, they like generally send us back like a really long document that covers like a ton of lines of like every part of the package that they look at on legal ease. Would we be able to like upload that back the system too.

13:36 - Conference Room (Team GoVisually) - Speaker 1
Yeah, absolutely. So you can upload that back into system and you can also add that. Um, so for example, here, uh, it's not related to what you're saying, but every project also has a document system. So here I've created like a, a creative brief for a juice packaging. Um, so you can also attach that and put that onto the system. So it doesn't have to be in a smart note, but if they sent it to you, you can also attach and keep it as part of reference. So in terms of how the label works, it typically goes through, oh, sorry, I'll just take you through another couple of things. So you'll notice that these ones only have a single version, but these have four versions, which means that each version gets stacked on top of another. So you've got a complete history from what happened from your first version all the way to your last version. To the one that's finalized. So when it gets to finalized, this is the point where no one else can add any more comments or feedback or any approval. So this becomes like your locked and loaded version that's going to be the one that's approved. Everyone knows it's approved and no one else can make any changes. So what happens there is, for example, if I was to click on here, you can see the entire history of what happened in terms of like who reviewed what, who requested changes, features, the entire activity feed. So you've got your full history on everything that happened on that particular Proof. So if you were ever to go back and wanting, you know, if you had an auditor that came in and said, hey, show me everything that happened because there was an error on this, you have the complete history. So you can print that out and show them, hey, we went through all the right processes and here's all the here's all the history. Another feature we have is the ability for you to add custom fields. So you can go ahead and create any sort of custom fields. I've gone ahead and created some basic custom fields here, but you can make it as comprehensive as you like, So if you had a piece of packaging that you'd like to add any sort of shelf life or certifications, et cetera, for example, you can go ahead and add that here. So in case, for example, here, you may say, hey, we ship this to you in Australia. United States, you can go ahead and add all of that information or allergen warnings, etc. And these are completely customizable. They can either be like a text field where you can add some text in or some notes. And this is per artwork, right? And what you can also do is you can group these your fields. For example, you may say, hey, I want to group these by ingredient certifications or shelf life. So it's really flexible on what you can do with those custom fields there. So far, I've taken you through how you can organize them into different sections, the different process in terms of how it flows from, you know, things requiring Review artwork that's been marked as requiring changes, who's marked them all as approved and who's locked, you know, once you final, it goes into a finalized state. And you have control over what you mark as finalized. So you have the ultimate say in what gets marked as finalized. So not anyone else. So we can have like a person assigned or two people, for example, you, yourself and Chelsea, or Ayaka, for example, can finalize something. So I'll take you through what happens when a when it comes to two versions.

17:25 - Sara R.
Can you un-finalize something once it's finalized?

17:28 - Conference Room (Team GoVisually) - Speaker 1
Oh, absolutely, yeah, you can.

17:31 - Sara R.
You'd be surprised by how often that happens.

17:35 - Conference Room (Team GoVisually) - Speaker 1
Yeah, yeah, absolutely. Not everyone can, so you can pick some people who can. So the admins can un-finalize it. So I'll show you how that works. I'm going to finalize this, but because I've got the... Authority to send it back for Review, I can send this back for Review. And you can see the complete history of, like I said, everything that's happened on this particular Proof, who's approved it. And you can also send reminders. For example, here, Sean, we've been waiting on him. So you can just come here and say, hey, can you send Sean a reminder? And that'll just nudge Sean to be able to come in and Review.

18:16 - CBollinger
It's

18:17 - CBollinger
That name is Sean. Because the person on our Team who will be most likely to get that reminder is also named Sean.

18:24 - Conference Room (Team GoVisually) - Speaker 1
There you go. I Read your mind. So we've got all the typical annotation tools here. You can come in. You can also tag folks in here. For example, hey, you may want to tag Laura. Say, can we make this bold? You can add attachments, add any sort of, you know, styling changes, etc. And essentially, as you add people, they'll get a notification saying, hey, you've been tagged, which I'll show you in a minute. And it's pretty simple. So you can either add a new either you can add a new annotation or a comment, or you can reply to one that's already on there. Now, imagine this has gone through a few changes. And Sara, as you were mentioning, you want to be able to see, hey, what's changed between the two versions, right? So we've got this side-by-side version, which is kind of gives you like a view on big changes. For example, if the background changed from blue to orange or something like that, you'll be able to see that. But if you want to be able to see that a little bit more closely, we have this overlay function, which allows you to be able to switch between the version and slide this and see what's changed. We also have the ability to have this functionality called split functionality. So what I'm going to do here is I'm going to Zoom in on this and you can see how the carbohydrate there had a spelling mistake and now it's been changed. The contain statement now also had a spelling mistake and that's now been changed in the new version. So it does a pixel pixel comparison of what's changed between the multiple revisions. So you could also go back to something, for example, say this had like six revisions, you can compare the first revision with your final revision to make sure that everything that's meant to be has been incorporated in your final before you Approve. There's also a diff functionality. This is more for This shows you what's changed between the two versions. So you can kind of do a diff. But most people tend to love the overlay and the split functionality. What side-by-side is good for is being able to check if these comments have been resolved. And then what you can do is you can come in here and say, oh, great, this was taken into consideration. For example, the USDA organic logo was added. I can now go ahead and mark that as resolved. So all your comments now get resolved. So you can be assured that as you're going through, making sure that your comments that are currently in red become turned into green, which means that you've gone through it and resolved it.

21:19 - CBollinger
And hey, one question on color. When you showed us color, one thing that's really big for us with packaging is differentiating between PMS colors and CMYK. Is there a Like, does the software get into that level of the file to Review it?

21:37 - Conference Room (Team GoVisually) - Speaker 1
I believe our AI functionality does, but I'm going to take a note on that and come back to Chelsea. Because some of that functionality is fairly new for us.

21:49 - CBollinger
And the reason that's important is because, you know, for like our cartoons, for example, we're charged by the number of colors. And so when an artist builds something and we can ask them, but we always have to mark out the color, whether it's PMS or CMYK. So it's helpful, A, to make sure that that is on the file, but also that we can tell if we have a question how the file is built, like, is that CMYK or is that Pantone?

22:16 - Conference Room (Team GoVisually) - Speaker 1
All right. I've taken a note on that. I'm going to come back to you just on that particular one. All right. So these are all I mean, I'm sort of breezing through some other functionality, but I think I'm just sort of focused on your pain points just so that I can and then we can sort of hone in on some of those questions in a bit. We also have this bird's eye view. So if you have someone who is in charge of managing the projects across the board, what this does, it gives you a complete bird's eye view across all your campaigns, all your projects, everything that's going on. So, for example, Here, I could say, hey, I've got 326 items that require Review. 35 have been marked as requiring changes. So I could say, hey, show me everything that's been marked as requiring changes across the board, right? And show me everything that's overdue or due in the next seven days overdue. So this gives me a complete list of things that I need to move through quickly because it's approaching a deadline. So you can do it at a project level, or you can also For example, if you guys were managing multiple things, come here and look at the whole thing.

23:32 - CBollinger
I may be getting ahead of things, but as we, like, onboard the system, can we customize some of those tags? I'm thinking specifically for our project manager. She checks, like, if a file's been released to the printer, if we've gotten the physical like there's very, there's steps within completed and approved that I think she would probably want to track.

24:03 - Conference Room (Team GoVisually) - Speaker 1
So the way we would do that is by using what's known as custom fields, which I was showing you earlier, right? So you could have one very specific for, I'm not sure what it is, but you can choose these different types of fields, like toggle, select, multi-select, and then being able to, so we also have You could even use, we have like this AI field generator, for example, if it's food and beverage, let me just see what happens.

24:32 - CBollinger
That's cool.

24:51 - Conference Room (Team GoVisually) - Speaker 1
Yeah, so this is great for getting some ideas as well on the types of things you may want to track. So for example here, It's got compliance, food, you know, these nutrition facts, or I could have said also add some steps in terms of those fine-grained steps that, sorry, who did you mention that was? Was that your regular triggers?

25:12 - CBollinger
Our project manager.

25:15 - Conference Room (Team GoVisually) - Speaker 1
Oh, your project manager, right. So you could add any of these fields. You can add them manually or use an AI field generator. So you can see here, for example, this one that I showed you earlier had these international So for example, you may want to come here and add.

25:30 - CBollinger
I'm just giving an example. So my question came up when you were showing us the other screen that was, like, approved, like, showing those different statuses. So is there a way to customize?

25:50 - Conference Room (Team GoVisually) - Speaker 1
Not at the moment. So we've kept this fairly linear that suits the needs of most companies, because essentially these are marked as files that, you know, either need change or they're approved or finalized. So what you're asking is, can you add more stages in here?

26:13 - CBollinger
Or so. Yes, exactly. It sounds like no. So between approved and finalized is that when you then you would tag it. So it's like approved. With the green tag, which means we've gotten the PDF.

26:27 - Conference Room (Team GoVisually) - Speaker 1
Yeah, so approved is essentially, you're happy on a particular, so every person gets to Approve or not Approve in that particular, whoever's in that process, right? So you may have an assigned person in brand or marketing or multiple people in brand or multiple people in marketing, and you'll be able to see here what they've done for that particular revision. So you may have, like, for example, Chelsea, you and Sara, you may be happy with it, but Ayaka may come and say, no, I need some more changes. So that gets flagged as requiring changes. It goes back into the process of being able to make those changes. And now it comes back into the Review process. Now, when all three of you mark it as, yep, we're all good, it's all looking pretty good, it comes up as an And now you can move that into, you can make the ultimate decision on, you can move that to a finalized.

27:24 - CBollinger
Got it. That makes sense. Can you go to the bird's eye view again?

27:27 - CBollinger
Yeah, sure.

27:29 - CBollinger
Cause, cause that, I think I forget what that. So it just lists all of those. And then do the tags show here that the custom tags.

27:41 - Conference Room (Team GoVisually) - Speaker 1
So it shows here. Oh, the custom tags. The custom tags don't show here. The custom tags show only in actual project view. So here we've got like your list view and your table view. So this one shows you all the custom tags here.

27:59 - CBollinger
Gotcha, gotcha. Okay, that's fine. Okay, that makes sense.

28:04 - Sara R.
And a question, and maybe this was in here, but like thinking about, I know that there's like projects and then pieces of artwork. So we can have like, for example, like a unit, a lid, and a carton all in one project. Oh, OK. Yeah, absolutely. And then it looks like we can also add, like we'll have secondary documents, like I create an Excel file that has all the UPCs for all pieces of artwork. It looks like we could upload that here as well.

28:35 - Conference Room (Team GoVisually) - Speaker 1
Yeah, sure, you can. Yeah, totally, totally. But I'm going to show you something more interesting with that, actually.

28:42 - CBollinger
I'm just so excited. I keep getting ahead of you.

28:45 - Conference Room (Team GoVisually) - Speaker 1
No, that's OK. That's OK. Please, please do jump in with your questions. OK, so what I'm going to show you is I'm going to switch gears and show you our AI suite. OK, so typically what you'll find is what we find is companies have some sort of SOP document like this. So this is just a sample one for a dummy company called mockup company called case craft. And you'll notice that they have like a sample checklist here of all the things. I mean, yours may not look like this, but typically the companies we work with will have something that looks like this. So again, so they may have something around ingredients, allergens, nutritional information, claims and marketing language. Essentially, it's kind of like their Bible of things they can or can't do. So this can be an format, really, like you sent me one that was more in Excel format, right? So this can also be turned into a series of checklists that's a little bit more, what do you call, detailed. For example, you may say that for our country of origin or manufacturer declaration net weight, these are the rules. Here's our phone number that has to be listed on there, right? So you can add all those rules in there, right? So essentially, this part of it, is managed by GoVisually, right? Our approval process. This part will be managed by AI. And this is essentially your version control, which is again managed by GoVisually, which I showed you, right? So I'm just kind of showing you how this will get translated into the different parts of the software. So do you guys have something like this already or is it mostly what you sent me?

30:35 - CBollinger
Sure don't.

30:36 - Conference Room (Team GoVisually) - Speaker 1
Okay, that's okay. You'll be creating one soon anyway. So it's fine. So it'll just make your life easier. So even if you don't have one, that's okay. We can help you with it. So what happens here is this is what we call as our AI playbooks. So you'll notice here that I have a ton of companies playbooks, which is in my demo account. So for example, I'm going to show you the one that I created for And what it is, is you can come here and upload this document or that Excel sheet you have. So you could have like a brand-specific or a product-specific guidelines, right? So here I've just got something that's quite long. So what the system does is it ingests that file and essentially codifies all that into a set of rules. So for a human to be able to do that, to go through this would be extremely time consuming. They'd be able to make a ton of mistakes. If you had someone new joining the Team, good luck because it would take them at least like, you know, four months for them to even figure out what needs to happen. So what happens here is we ingest and we create them into a set of rules. So for example, this one you can see here, these are called validation rules. So you'll notice that some of these are critical. Some are must require brand name, must match mark registration exactly. Ingredient list must start with ingredients in bold. Ingredients list ordered by weight, right? So we've got all of these rules that it's been codified. There's also calculation rules. So for example, if you've got a salt calculation or sodium euro, so they have a particular calculation, this only has a single calculation, and this gets turned into a CR rule, a calculation rule. Then you have pattern rules. Example, date formatting, right, that needs to be in a particular format. So what happens is we ingest that into the system, and you've got a series of agents. So this AI agents, the first one is the, I'll just see, I think someone may have joined, just let me have a quick look. Oh, John's joined.

32:54 - Sara R.
He goes by Wesley, just FYI.

32:56 - Unidentified Speaker
Oh, Wesley.

32:58 - Sara R.
No, you would not know that.

32:59 - Conference Room (Team GoVisually) - Speaker 1
Hi, Wesley. Thanks for joining. Hi, Wesley. Thanks for joining. We're just getting through the meaty part of the software, which is the AI part. So I was just showing the Team how, you know, you may have some sort of an SOP or a checklist or an Excel sheet, both at a brand, sort of at the brand level or at a particular product level, what we do is we ingest that and we create a set of rules. So, for example, here's like validation rules, calculation rules and pattern rules, right? So as you update this document Team, so you would just come here and upload a new document. We're also providing the ability for you to edit that and keep those rules updated on the system. So in terms of agents, this agent here, the compliance auditor, essentially checks everything in that particular knowledge base and makes sure that on the packaging it does a comparison. And then we also have, for example, if you were to ever export to another market, we have different agents. So in your case it would just be the FDA agent, but we also have different So we even have something known as a visual elements inspector validator. So for example, if you needed to make sure that certain packaging had to have an USDA logo or a kosher or a halal symbol, for example, this will automatically check and flag if that's missing. And again, you can set that up in your rules. Now coming to how these rules get applied. So you'll notice here, as soon as you upload an artwork, the agents go to work, right? So the agents have now, for example, in this case, this is another label from a European company. You'll notice that this agent has automatically run in the background, and it's run the auditor agent, the image check agent, and the spelling agent. So clicking through here, it'll immediately show you that it ran 15 items, nine items, items were successful, four failed and two partial. So you'll notice here there's four agents that ran. They're all distinct, distinctive. Think of it as like these as being your co-workers, right? So you may have like an auditor in your Team that's just auditing labels based on your requirements. Someone who's checking for logos and pictograms and making sure they're all in the right spot. Someone from the regulatory Team making sure that it meets regulation. In this case I haven't run the regulatory one but you can see how it works. For example, here now it's called out that some of the allergens that were meant to be listed in bold have not been listed in bold because I have a requirement that allergens even in the statement have to be marked as bold. And you can see which rule ran. So in this case it's the VR002, VR003 that was converted it from their document into a set of rules. Does this make sense so far? I'm thirsty.

36:21 - Sara R.
I just keep being like, how much can we trust it versus having a regulatory? But my thought is, even if we use it before it goes to an official regulatory check, that they should need, like, we have a final expert check it, it should have many fewer issues before it gets through.

36:39 - Conference Room (Team GoVisually) - Speaker 1
Oh, absolutely. Don't you worry, we make a disclaimer saying that, hey, this uses AI, so, you know, you should always get a compliance expert or a human to check it, right? So, like, as you said, Sara, essentially what it is, it's your first pass, right? A lot of things that potentially tied eyes after you've seen it like five times can miss is this is what will pick it up for you and say, hey, you know, you missed this, right? So, we've had a lot of teams pick up, you know, they've said, You saved our butt. This thing saved our butt because even when we had a lawyer involved, we missed certain things because sometimes a lawyer may miss certain visual elements or some of the things that you mentioned around like branding, for example, they may miss that because they're not trained for that, right?

37:29 - Sara R.
And they're human. Ultimately, part of this is trying to take as much of the human error aspect out of it, even just like the tools to be able to compare artwork against each other. Like that for me is the hardest part where I personally know I make the most errors because it's so hard after you've looked at the same thing over and over and over again. That you like, I frankly, we are just like not like as all of us being human beings, like we're just not equipped to do a good job of, I've heard Sean say it. He's like, after the second time I'm done. But I mean, frankly, I mean, we keep doing it, but I am terrified that we are making mistakes because it's hard.

38:15 - Conference Room (Team GoVisually) - Speaker 1
That's exactly right. I mean, we've heard this over and over again, and hence why we built this. So one of the other things you can do, for example, is we have something known as Gia, which is your AI assistant. And this thing is really, really smart in terms of if you ever had any questions, you can ask it further qualifying questions saying, hey, what about this? And this is essentially you're talking to the artwork now. So you can go in and get it to do things like like you said, you can compare the previous version. You can say, hey, by the way, I may need to present this to my seniors tomorrow. So can you actually come up with a list of things that from a branding sense, does it meet You can also get it to do some really cool things. Hang on, let me just move this out of the way. For example, you can even get it to create a 3D image. So over here, I took this from NutriBio, which I showed you the video of I just asked it to create a hyper-realistic 3D image of this used in the gym. So it'll create, like, generate, like, an image instantly, right? You can create social media content. It'll give you, like, yeah. That is wild.

39:33 - Sara R.
I mean, also really terrified for people's jobs, but that's crazy that it could do that. We're having agencies do that work right now.

39:42 - JohnWesley
It's not that terrifying for jobs. It makes your jobs easier.

39:45 - Sara R.
It makes our jobs easier, but it takes away jobs from other people.

39:48 - Sara R.
Not really.

39:49 - Sara R.
I don't know. Amazon just did 13,000 layoffs.

39:55 - JohnWesley
Yeah, the excuse has nothing to do with the reality.

39:59 - Conference Room (Team GoVisually) - Speaker 1
though yeah I know there's there's definitely a lot of that too yeah look I think we all we none of us know where it's going it um but yeah like you said yeah it's um it's it's amazing how much it can do that was previously being done by you know teams of people or humans so in a way it is kind of like but I think we're gonna find that through all the different tech revolutions I mean I'm a bit of an old So I've been I've been around for a while and I was I've always been constantly worried through the different phases like there was like the dot-com boom and there was like the The cloud thing people always said hey, you may lose your job here, but we've all survived you evolve Yeah The more it can do the more you have to do the more you have free time to do other things the more things you have to do.

40:51 - Sara R.
Oh, I mean for us I'm super excited for other people as well And we're a small company.

40:57 - JohnWesley
I don't think that's really a concern for us, to be honest. I mean, we're a globally known company, but we have a small Team in reality.

41:07 - Conference Room (Team GoVisually) - Speaker 1
So think of it as being you having your own little personal assistants that are doing some of these groundwork for you. So you have time to do more interesting things.

41:15 - Sara R.
That's really cool, too. I mean, Chelsea, I think about what he's showing us right now, if it could create e-commerce banners for us. Can it do different sizes?

41:25 - Conference Room (Team GoVisually) - Speaker 1
Sorry, different?

41:26 - Sara R.
Different sizes, yeah.

41:27 - Conference Room (Team GoVisually) - Speaker 1
Yeah, it can. Yeah, totally. You can just, yeah. So we soon actually have like what's known as a where you can just select the library and say, make this, make this, make this. So yeah, so all that's coming up soon. But right now you just have to punch it in. Okay, cool. So in here you can do like a lot of other things as well.

41:54 - JohnWesley
So is a lot of this machine learning or is it AI?

42:00 - Conference Room (Team GoVisually) - Speaker 1
It's a combination of two things, Wesley. So we use best of class models to do different things, right? So we've got a combination of different models that are off the shelf models, but we've also got some fine-tuned models that that work on, for example, this checklist here that we converted into a particular and using our dynamic compliance auditor, for example, uses our own trained model to understand the nuances that a foundational model may not understand. So it's a combination of things.

42:41 - JohnWesley
And is our data In its own silo.

42:45 - Conference Room (Team GoVisually) - Speaker 1
It's in its own silo. Yeah, so we've got I don't want to train other people with our now with our data No, we've got we've got agreements with all of them because we are a vendor We have that they don't get to train many of this data with yeah, so it's all right guys.

42:59 - JohnWesley
That's the IT talk. Sorry Apologizing the rest of Team is the IT.

43:05 - Conference Room (Team GoVisually) - Speaker 1
Oh, that's okay. Yeah, and that's good questions though. We get that a lot. Yeah, so you can use the chat functionality to do a whole bunch of things, including like trademark checks, or it'll go out and do competitor analysis. I mean, there's no limits to what you can do. So Wesley, I've sort of taken everyone through all the sort of foundational core functionality in terms of revision management, being able to manage managed across the different states, adding custom peels, version comparison, version stacking, reporting.

43:46 - JohnWesley
Stuff they really care about.

43:49 - Conference Room (Team GoVisually) - Speaker 1
We were just getting into the meaty part of the AI stuff. So yeah. You joined at the right time.

43:55 - JohnWesley
Does GoVisually plug into other applications that are out there or services like TraceGames or other regulatory stuff?

44:03 - Conference Room (Team GoVisually) - Speaker 1
Not at the moment, no. What would be, for example, the use case there?

44:10 - JohnWesley
Not even sure. Just asking.

44:12 - Conference Room (Team GoVisually) - Speaker 1
No, not at the moment. We plug into a lot of the project management system. So we've got integration with Asana, Adobe. Oh, actually, did Chelsea just drop? Perhaps she's got some.

44:29 - Sara R.
I think she just has her camera off.

44:31 - Unidentified Speaker
Oh, camera off. Yeah, I'm here. I just had to run to the door.

44:34 - Conference Room (Team GoVisually) - Speaker 1
Yeah, that's OK. Yeah, so we've got integrations directly with Adobe. That's what I was going to mention yesterday, which I was going to show you. So I'll just share this video that shows you how we integrate directly. So your designers, all the stuff that I've shown you so far, it's so tightly integrated with Adobe. I'll just show you how that works. Let me know if the audio works here, because sometimes it can be a little choppy.

44:57 - Conference Room (Team GoVisually) - Speaker 2
Hi, today.

44:58 - Conference Room (Team GoVisually) - Speaker 1
Does that work? It did, okay. Excuse the robotic audio.

45:05 - Conference Room (Team GoVisually) - Speaker 2
Hi, today I'll show you how GoVisually integrates directly with Adobe Photoshop, InDesign and Illustrator. As you can see on this Proof, my Team members have left several comments requiring changes to this Proof. Now, jumping into Photoshop with the GoVisually plugin, I can immediately see all the projects I'm involved in. Let's click on this here. I can see all the proofs with all the feedback. I can immediately see this one requires me to change the background to blue. So let's go ahead and do that. We can now resolve this comment and move to the next one. This one requires me to change the copy to oak. I'm going to go ahead and make that change. Once these are resolved, I can now add a new revision. This will automatically update when I switch back to Go Visually. Your reviewers can now immediately see there's a new revision. Clicking on this shows them the new revision with all the changes. You can also compare the before and after using the Compare button.

46:13 - Conference Room (Team GoVisually) - Speaker 2
That's nice.

46:19 - Sara R.
Too bad we don't have our own in-house designers. I was like, this would be so great if we had an in-house But I don't, I don't have to be in-house.

46:29 - Conference Room (Team GoVisually) - Speaker 1
They don't have to be. They don't have to be.

46:32 - Sara R.
But they have to be, they have to be integrated into the system, which depending on who we use, I guess would be fine.

46:38 - CBollinger
Well, so for example, we have a freelance person, like what are the requirements to tie in someone to this system?

46:46 - CBollinger
Can I count the plugin?

46:49 - Conference Room (Team GoVisually) - Speaker 1
As long as it, so the plugin just requires a GoVisually. So even if they're using their own Photoshop or most of them use Illustrator, obviously for packaging design, even if they have their own license, the agency license, they will just need a GoVisually account and they can just sign into the plugin. The plugin is separate to the Adobe license.

47:10 - CBollinger
Sounds would work. Super cool.

47:15 - Conference Room (Team GoVisually) - Speaker 1
We have tons of customers where the freelancer is outside the company and they still use the functionality. So it's not a problem.

47:23 - CBollinger
That's amazing.

47:25 - Conference Room (Team GoVisually) - Speaker 1
All right. So I'm sort of going through everything at like a thousand miles an hour. So let's open the floor for any questions. And if there's anything else you'd like me to dive into, what do you think?

47:37 - JohnWesley
So is there like a dashboard that kind of shows all the projects that they have going on and a project view what the deadlines for each of them are, Gantt view kind of stuff.

47:50 - Conference Room (Team GoVisually) - Speaker 1
Yeah so we have something I obviously showed up late.

47:54 - Sara R.
Yeah man he already showed us all this stuff. You're too late.

47:57 - JohnWesley
Okay then maybe uh maybe if they're happy I don't I don't care.

48:00 - Unidentified Speaker
We we think it's very cool.

48:04 - Conference Room (Team GoVisually) - Speaker 1
Yes yes to answer your question Wesley there is uh what we call as a bird's eye view that shows you across the board um view across everything that's happening.

48:14 - JohnWesley
Is app for for people who are doing things on the run to just like look at stuff.

48:21 - Conference Room (Team GoVisually) - Speaker 1
So we have an iOS app. We've got an Android coming up soon, but I believe most of the States is on iOS.

48:28 - CBollinger
Holy cow. I was like expecting, I know we're working on that.

48:34 - Conference Room (Team GoVisually) - Speaker 1
We only use iOS.

48:35 - JohnWesley
So that's perfect for us. I just imagine myself looking at my phone, looking That was actually something that your VP had interest in.

48:48 - Sara R.
Oh, it's fascinating that she is doing that on a phone. I got to get her to get me a better phone.

48:57 - CBollinger
I think coming off of Wes's question regarding a Gantt chart, does the Bird's Eye View have a Gantt chart, like timeline?

49:06 - Conference Room (Team GoVisually) - Speaker 1
Not yet, but we've got We've got two big things coming up of some like a Gantt chart style thing showing you the timelines. And we also have a task management that's coming up. So it'll sort of assign tasks to people. So that's slated for Q. We're starting working on the Q4, which is already sort of started, but will be released in the Q1 of next year.

49:33 - Sara R.
So we can see. So we can see how saw everyone who still needs to Review and we can nudge them like you showed us, but now their future state, it'll be even easier to do that?

49:52 - Conference Room (Team GoVisually) - Speaker 1
No, it's basically just a different view. So every asset, for example, has a due date, right? So where you can assign like a due date. What a Gantt chart would show you is essentially how it's being, you can see basically like a horizontal view of when things are due and where asset's at play. So you can, for example, see that, you know, there's four people here, we're getting close to the due date, but there's still four people waiting. So yeah, it's just a different view of the bird's eye. What's the timeline you were looking at to get something in place, and do you have any?

50:36 - CBollinger
I'll let Wes answer that from a realistic standpoint, but as soon as possible from our end.

50:44 - JohnWesley
Yeah, I don't know that we even have a pricing or any details on average time that you guys kick things off and completion.

50:56 - Conference Room (Team GoVisually) - Speaker 1
We can get a pricing out to you this week or early next week, just I just need a few more questions answered, which we can do it through email, honestly. In terms of getting started, you could, I mean, one of the beauties of GoVisually is it doesn't require any, you know, massive amounts of training or onboarding or any of that. We have most people just getting started. They get started with one project and then just try it with like a smaller number of people and then just sort just bring on the whole organization or anyone else you need to bring on. It's got a really good sound.

51:37 - Sara R.
That sounds sounds great. Sounds simplified, certainly. And I mean, after like seeing the tool, I that makes sense to me, especially I imagine like, a marketing Team doing the first project, and then we could expand it out into everybody else that needs to Review things people like R&D. I think but it does feel like very intuitive, especially for people who are just checking things versus like those of us who need to own projects. I think it's a little more onerous on the people that need to own projects, but, um, for, for people like R and D that just need to have a look and say like, yes, no comments. It seems very straightforward.

52:21 - JohnWesley
Well, I just, uh, I partially was asking you because I remember that whole thing that we were doing in Workfront and all of these very specific areas that some people were very, very, very concerned with. And does it translate into this?

52:37 - Sara R.
I think this tool actually is a much better fit because it was built with this in mind. And these guys have worked in the space and understand what questions we have or how we think about it. You can customize on the fly with within the tool, but there's a lot of it that's already kind of set up for what we need.

53:01 - JohnWesley
Packaging companies that it might go out to, however many colors might be needed, and our own codes that might be associated.

53:11 - CBollinger
Yeah, I think the problem with Workfront was that it was intended to replicate our routing system, and that's probably where it got bogged down. I think the opportunity The opportunity here is to optimize our routing system using Go visually, I think.

53:31 - JohnWesley
Modernize our routing system, maybe.

53:35 - CBollinger
I think that said, though, there are key players that I think we need to bring on board to maybe ask more detailed questions. I'm thinking of Emond. So Emond is our packaging project manager, and he's the that I was mentioning like would need to look at colors. He's very specific, like he zooms into like a million percent and looks at like the compilation of the lines. And so he's the one who really manages our process. And I just want to make sure that he's comfortable, that the system can do all the things that he needs and that we just get him feeling good about this transition. So I didn't bring him today because he has very technical questions that I just didn't, I didn't want want to throw you off in showing kind of an overview, but I think he would he may be another stakeholder that we should work closely with.

54:30 - Conference Room (Team GoVisually) - Speaker 1
Yeah, absolutely. Happy to have even like a one on one Meeting, just going through all the techie kind of bits of it. So happy.

54:41 - CBollinger
So his face, I adore him. He's wonderful. And he saves our ass all the time. Like, he's incredibly knowledgeable. But he does have very detailed processes because he needs to get it right when the stuff prints.

54:55 - Conference Room (Team GoVisually) - Speaker 1
No problems. No, I'm happy to have a conversation with him. I'll be upfront if something's not possible, I'll let him know that it's being built or coming up. I think the main thing is to look at it is we'll go visually solve about 80 percent of your problems. We're never going to be like 100 percent there. No software ever is. But what we can do is like, As Sara mentioned, we're working specifically in this industry, so we spend a lot of time understanding your needs. So we're evolving really rapidly to be able to fill any gaps we have. But I'm happy to have that conversation, taking through a demo and making sure that he's happy with the things that he wants to get out of it. Yeah, for sure.

55:38 - CBollinger
And then Wes, let's connect on sort of next steps internally. I imagine pricing is a big piece of it, but I think... 29.99. Yeah, please. That sounds great. Or maybe a couple more nines. I don't know. I'm sure there's much else we can do except getting a Meeting with Eman to drive the process. So Wes, just let us know where you need us to plug in.

56:06 - JohnWesley
On the IT side of things, I'm going to talk to Gartner. Compare go visually to anybody else. If you guys are the magic quadrant, everybody else is super far left field, it makes it a lot easier for me. But if there's a couple of other players that compare to you guys, then we'll have to do conversations with them as well so that the Team has a reasonable understanding of what's out there and they can make an honest decision about which direction they want to go. Then there's, of course, the pricing. We send all of our pricing over to them as well a lot of their other customers do, so we can see how honest the pricing really is. And that's just part of the IT side of things.

56:48 - Conference Room (Team GoVisually) - Speaker 1
Yeah, not a problem. So look, I'm happy to work with you, Wes, just on that. Should I call you Wes or Wesley?

56:55 - JohnWesley
I don't want to. Wes, Wesley is fine.

57:01 - CBollinger
I worried when Sara said he goes by Wesley. I was like, oh, shoot, I've been butchering that for a long Yeah, so we can work through that.

57:15 - Conference Room (Team GoVisually) - Speaker 1
Yeah, I mean, it's, we're relatively, what do you call it? A nimble sort of company, so we can move quickly. We don't have too many processes. So, I mean, we started the company as purely a self-serve company, but now as the software has evolved, we like to show people how, it solves that problem. So we get on these calls, but you know, honestly, you can even get started without me. So it's very intuitive and easy to use.

57:47 - JohnWesley
That's better than the multiple months long process of failure that we went through with Workfront. Workfront, yeah.

57:55 - Conference Room (Team GoVisually) - Speaker 1
You'll be up and running in three days, max. No, no.

58:02 - JohnWesley
Are you sure?

58:07 - Conference Room (Team GoVisually) - Speaker 1
At least you'll be able to get some value out of it, right? So the initial part of being able to move an artwork through a fairly simple linear process, you'll be able to see that value straight away. And as a sort of second phase, we could add a little bit more, you know, as you sort of go and how you need it. And then the third phase we can add all the AR functionality.

58:29 - JohnWesley
Yeah, as far as like at the end of the day when we're talking about the budget, if your average client goes from a six-week process down to a four-week process or an eight-week process down to a three or four-week process, that really helps me when I'm talking about sales or the cost and getting approvals. Yeah, sure, sure. Because I know our process right now and for the last 18 years been a nightmare and it's slow and it's I think Chelsea was saying it was what eight weeks like I mean it can be best case like like three yeah I always thought it was like six months but to be clear we're talking about getting you as a vendor we set up in the system not like us being able to use the tool no no I was talking about like project going in and process time For a single piece of artwork, it can take up to three months.

59:30 - CBollinger
Some are faster if they're more rudimentary. The entire writing process for a new project is probably six months just because the timelines are spread out because some items have longer lead times. But all of this is helpful to shorten that.

59:48 - JohnWesley
And is it possible some of those lead times are long because of how long the process takes us?

59:56 - CBollinger
Partially, I mean, no, the long lead times I'm talking about are like literally to get things over oceans.

1:00:02 - Unidentified Speaker
Got it.

1:00:03 - CBollinger
So like we can't fix that, but certainly the entire timeline for the project can shave off some time if this routing is faster.

1:00:12 - JohnWesley
Yeah, Chelsea, besides working on this project with your Team, there's a project I'm working on with R&D. They're already paying for the new project, so it should help them a lot. And that should help them speed up a lot of the processes they have going on that really make what they do take longer than it should.

1:00:38 - CBollinger
That's great. But are there any potential overlaps to this system? That was something that crossed my mind.

1:00:44 - JohnWesley
This is all regulatory. Very realistically, it's about their recipes and the regulatory. There is some kind of an overlap, but not really in the nutrition section. It has some capabilities to do stuff for the nutrition stuff that would make it easier potentially for you guys.

1:01:08 - CBollinger
Do you foresee any issues getting R&D up and running on this system?

1:01:13 - JohnWesley
Not at the moment.

1:01:15 - Unidentified Speaker
Okay, cool.

1:01:23 - Unidentified Speaker
Well, I have to run, but thank you so much for this.

1:01:26 - Unidentified Speaker
No problem.

1:01:27 - CBollinger
So I think next steps on our end, let me connect with Emund, our packaging manager. And maybe if I just connect you to an email, would that be okay?

1:01:39 - Conference Room (Team GoVisually) - Speaker 1
Yeah, that's fine. All right. Chelsea, I think you're away for a week, correct? On a vacation.

1:01:48 - CBollinger
Two weeks. Where are you off to? My little brother is getting married in Hawaii. I figured to the point where I was going all the way over there, I might as well stay there for a bit.

1:02:04 - Conference Room (Team GoVisually) - Speaker 1
That's the way to do it.

1:02:05 - Conference Room (Team GoVisually) - Speaker 1
Very excited.

1:02:07 - CBollinger
So yeah, I mean, continue. But it'll be very nice family time. So we're excited. But that said, do not slow this process down. All systems go full speed ahead. Sara can take it over.

1:02:24 - Sara R.
I was going to say anything you need, just reach out to me.

1:02:28 - Conference Room (Team GoVisually) - Speaker 1
Sara, do I have your email ID on that invitation? I'm just checking.

1:02:33 - CBollinger
I forwarded it, so perhaps not. I'll just drop Sara's email into the chain from setting up this Meeting.

1:02:47 - Conference Room (Team GoVisually) - Speaker 1
Well, that sounds great. Chelsea, you have a great vacation and we'll continue conversations and yeah, enjoy the wedding. John, sorry, Sara, Ayaka, thank you for your time. We'll be in touch.

1:03:02 - Unidentified Speaker
No problem."""

def parse_timestamp(time_str):
    """Convert timestamp from M:SS or H:MM:SS format to seconds"""
    parts = time_str.split(':')
    if len(parts) == 2:
        # M:SS format
        minutes, seconds = int(parts[0]), int(parts[1])
        return minutes * 60 + seconds
    elif len(parts) == 3:
        # H:MM:SS format
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    return 0

def parse_transcript(text):
    """Parse the transcript text into speaker blocks"""
    lines = text.strip().split('\n')
    speaker_blocks = []
    speakers_set = set()
    
    # Base timestamp for Oct 30, 2025 (assuming meeting starts at 9:00 AM Pacific)
    base_datetime = datetime(2025, 10, 30, 9, 0, 0, tzinfo=timezone.utc)
    base_timestamp = int(base_datetime.timestamp())
    
    i = 0
    current_speaker = None
    current_words = []
    current_start_time = None
    
    # Skip header lines
    while i < len(lines) and not re.match(r'^\d+:\d+', lines[i]):
        i += 1
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if line matches timestamp pattern (e.g., "0:53 - Speaker Name")
        match = re.match(r'^(\d+:\d+(?::\d+)?)\s*-\s*(.+)$', line)
        if match:
            # Save previous block if exists
            if current_speaker and current_words and current_start_time is not None:
                end_time = parse_timestamp(match.group(1))
                speaker_blocks.append({
                    "start_time": base_timestamp + current_start_time,
                    "end_time": base_timestamp + end_time,
                    "speaker": {"name": current_speaker},
                    "words": " ".join(current_words)
                })
            
            # Start new block
            current_start_time = parse_timestamp(match.group(1))
            current_speaker = match.group(2).strip()
            current_words = []
            speakers_set.add(current_speaker)
            i += 1
        else:
            # Continuation of current speaker's words
            if line and current_speaker:
                current_words.append(line)
            i += 1
    
    # Add final block
    if current_speaker and current_words and current_start_time is not None:
        # Estimate end time (add 5 seconds for last block)
        end_time = current_start_time + 5
        speaker_blocks.append({
            "start_time": base_timestamp + current_start_time,
            "end_time": base_timestamp + end_time,
            "speaker": {"name": current_speaker},
            "words": " ".join(current_words)
        })
    
    speakers = [{"name": name} for name in sorted(speakers_set)]
    
    return speaker_blocks, speakers

# Parse the transcript
speaker_blocks, speakers = parse_transcript(transcript_text)

# Extract unique participants from speakers
participants_map = {
    "CBollinger": {"name": "CBollinger", "first_name": "Chelsea", "last_name": "Bollinger", "email": "cbollinger@nissinfoods.com"},
    "Sara R.": {"name": "Sara R.", "first_name": "Sara", "last_name": "R.", "email": "sara.r@nissinfoods.com"},
    "Ayaka Morimoto": {"name": "Ayaka Morimoto", "first_name": "Ayaka", "last_name": "Morimoto", "email": "ayaka.morimoto@nissinfoods.com"},
    "JohnWesley": {"name": "JohnWesley", "first_name": "Wesley", "last_name": "John", "email": "wesley.john@nissinfoods.com"},
    "Conference Room (Team GoVisually) - Speaker 1": {"name": "Conference Room (Team GoVisually) - Speaker 1", "first_name": "GoVisually", "last_name": "Team", "email": None},
    "Conference Room (Team GoVisually) - Speaker 2": {"name": "Conference Room (Team GoVisually) - Speaker 2", "first_name": "GoVisually", "last_name": "Team", "email": None},
    "Unidentified Speaker": {"name": "Unidentified Speaker", "first_name": None, "last_name": None, "email": None}
}

participants = []
seen_participants = set()
for speaker in speakers:
    speaker_name = speaker["name"]
    if speaker_name not in seen_participants:
        seen_participants.add(speaker_name)
        if speaker_name in participants_map:
            participants.append(participants_map[speaker_name])
        else:
            # Default for unknown speakers
            participants.append({
                "name": speaker_name,
                "first_name": None,
                "last_name": None,
                "email": None
            })

# Meeting metadata
meeting_title = "[CPG] - Nissin Foods USA - Demo"
meeting_date = datetime(2025, 10, 30, 9, 0, 0, tzinfo=timezone.utc)
start_time = meeting_date.isoformat()
# Meeting duration appears to be about 63 minutes (from 0:53 to 1:03:02)
end_time = (meeting_date.replace(hour=10, minute=3)).isoformat()

# Payload in the specified format
# Use a unique session_id each time to avoid idempotency duplicates
import uuid
unique_session_id = f"test-{uuid.uuid4().hex[:12]}"
payload = {
    "session_id": unique_session_id,
    "trigger": "meeting_end",
    "title": meeting_title,
    "start_time": start_time,
    "end_time": end_time,
    "participants": participants,
    "owner": participants[0] if participants else {"name": "CBollinger", "first_name": "Chelsea", "last_name": "Bollinger", "email": "cbollinger@nissinfoods.com"},
    "summary": "Demo meeting for GoVisually platform showcasing packaging workflow management, AI compliance checking, version control, and integration capabilities for Nissin Foods USA team.",
    "action_items": [
        {"text": "Connect with Emund (packaging project manager) for technical questions"},
        {"text": "Get pricing information to team"},
        {"text": "Schedule follow-up meeting with Eman"},
        {"text": "Review Gartner comparison for GoVisually"}
    ],
    "key_questions": [
        {"text": "Can the system differentiate between PMS colors and CMYK?"},
        {"text": "How does the AI compliance checking work for FDA regulations?"},
        {"text": "What integrations are available with other systems?"}
    ],
    "topics": [
        {"text": "GoVisually platform overview"},
        {"text": "AI compliance and regulatory checking"},
        {"text": "Version control and artwork comparison"},
        {"text": "Adobe integration"},
        {"text": "Custom fields and workflow customization"}
    ],
    "report_url": "https://app.read.ai/analytics/meetings/SESSIONID",
    "chapter_summaries": [
        {
            "title": "Platform Introduction",
            "description": "Overview of GoVisually platform capabilities for packaging workflow management",
            "topics": [
                {"text": "Project organization"},
                {"text": "Review and approval workflow"}
            ]
        },
        {
            "title": "AI Compliance Features",
            "description": "Discussion of AI-powered compliance checking, FDA regulations, and automated validation",
            "topics": [
                {"text": "AI playbooks"},
                {"text": "Compliance auditing"},
                {"text": "FDA regulations"}
            ]
        },
        {
            "title": "Integration and Customization",
            "description": "Adobe integration, custom fields, and workflow customization options",
            "topics": [
                {"text": "Adobe plugin"},
                {"text": "Custom fields"},
                {"text": "Workflow stages"}
            ]
        }
    ],
    "transcript": {
        "speaker_blocks": speaker_blocks,
        "speakers": speakers
    },
    "platform_meeting_id": None,
    "platform": None
}

# Prepare headers
headers = {"Content-Type": "application/json"}
if readai_secret:
    headers["X-ReadAI-Secret"] = readai_secret

# Send POST request to webhook
print("📋 Payload summary:")
print(f"   Session ID: {payload['session_id']}")
print(f"   Title: {payload['title']}")
print(f"   Participants: {len(payload['participants'])}")
print(f"   Transcript blocks: {len(payload['transcript']['speaker_blocks'])}")
print(f"   Transcript speakers: {len(payload['transcript']['speakers'])}")

# Verify transcript content
total_words = sum(len(block.get('words', '')) for block in payload['transcript']['speaker_blocks'])
print(f"   Total transcript words: {total_words:,}")
if payload['transcript']['speaker_blocks']:
    first_block = payload['transcript']['speaker_blocks'][0]
    last_block = payload['transcript']['speaker_blocks'][-1]
    print(f"   First block: {first_block.get('speaker', {}).get('name', '?')} - {first_block.get('words', '')[:50]}...")
    print(f"   Last block: {last_block.get('speaker', {}).get('name', '?')} - {last_block.get('words', '')[:50]}...")

# Verify payload size
import sys
payload_json = json.dumps(payload)
payload_size = len(payload_json.encode('utf-8'))
print(f"   Payload JSON size: {payload_size:,} bytes ({payload_size / 1024:.1f} KB)")
print()

try:
    print("🚀 Sending webhook...")
    response = requests.post(
        webhook_url,
        json=payload,
        headers=headers,
        timeout=30
    )
    
    # Print response details
    print(f"\n📥 Response Status: {response.status_code}")
    
    try:
        response_json = response.json()
        print(f"📄 Response Body:")
        print(json.dumps(response_json, indent=2))
        
        # Check if request was successful
        if response.status_code == 200:
            if response_json.get("ok"):
                print("\n✅ Webhook accepted successfully!")
                if "event_id" in response_json:
                    print(f"   Event ID: {response_json['event_id']}")
                if "idempotency_key" in response_json:
                    print(f"   Idempotency Key: {response_json['idempotency_key']}")
                print("\n💡 Next steps:")
                print(f"   1. Check worker logs: docker-compose logs -f worker")
                print(f"   2. Check debug endpoint: {base_url}/debug/events/{response_json.get('event_id', 'EVENT_ID')}")
                print(f"   3. Check Zoho CRM for Lead updates (matching by email: {payload['participants'][0].get('email', 'N/A')})")
            else:
                print(f"\n⚠️  Webhook returned ok=false")
        else:
            print(f"\n❌ Webhook request failed with status code {response.status_code}")
    except json.JSONDecodeError:
        print(f"📄 Response Body (non-JSON):")
        print(response.text)
        if response.status_code == 200:
            print("\n✅ Webhook accepted (non-JSON response)")
        else:
            print(f"\n❌ Webhook request failed with status code {response.status_code}")
        
except requests.exceptions.Timeout:
    print(f"\n⏱️  Request timed out after 30 seconds")
    print("   The webhook may still be processing. Check worker logs.")
except requests.exceptions.ConnectionError as e:
    print(f"\n🔌 Connection error: {e}")
    print(f"   Make sure your API is running at {base_url}")
    print(f"   If using Docker: docker-compose up")
except requests.exceptions.RequestException as e:
    print(f"\n❌ Error triggering webhook: {e}")
