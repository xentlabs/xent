# TODO: this file needs to be cleaned up to better fit with the new stateful design of text generation
import random

import torch

from xent.runtime.text_generation.text_generation import TextGenerator

NARRATIVE_SEEDS = {
    # Gemini:
    "Gothic Horror": "The decay of the house was not a thing of mere wood and stone, but a rot of the spirit, a creeping miasma of forgotten sorrows that had soaked into the very mortar, such that to breathe the air within its halls was to inhale the dust of long-dead resentments and the faint, cloying perfume of madness.",
    "Bureaucratic Memo": "ACTION ITEM: Q3 Synergy Mandate. Per the executive directive issued 10/26, all departmental units are required to interface with the new Project Phoenix middleware for cross-platform deliverable tracking. Failure to achieve 95% compliance by EOD Friday will negatively impact Q4 budget allocations. Please cascade this information to your respective verticals.",
    "Casual Food Blog": 'OMG you guys, you HAVE to try this new brunch spot, "The Gilded Spoon." I got the avocado toast with chili-infused honey and it was literally life-changing. L-I-T-E-R-A-L-L-Y. The aesthetic is super vibey, all reclaimed wood and Edison bulbs. 10/10 would recommend.',
    "Archaic Epic": "Hark, for in the age of ember and ash, when mountains were but babes, did the Sky-Titan forge the Sun-Hammer, its head a captive star, its haft the bone of a god, and with a single, resounding blow, did He strike the Anvil of Night, and from the sundered sparks were born the constellations.",
    "Stark Survival Log": "Day 27. The hunger is a dull ache now. Ate the last of the lichen yesterday. The wind never stops. Saw another set of tracks this morning, not animal. Larger. I have three cartridges left for the flare gun. I will not use them to signal.",
    "Experimental Second-Person": "You are in a room with no doors. The walls are the color of a television tuned to a dead channel. You have a single key in your pocket, but there are no locks. You feel an inexplicable urge to apologize.",
    "Court Transcript": "MR. HENDERSON: And can you tell the court, precisely, what you observed?\nWITNESS: I saw the defendant. He was... well, he was rearranging the garden gnomes.\nMR. HENDERSON: Rearranging them how?\nWITNESS: Into what appeared to be a diorama of a famous naval battle. I believe it was the Battle of Trafalgar. His attention to detail was impressive.",
    "Cyberpunk Jargon": "Just slotted a new firmware patch for my optic nerve. The KORP-issued ad-blocker was starting to glitch, letting targeted psych-ads bleed into my REM cycle. Had to splice in a black market Ghost-filter I bought off a data-dredger in the Neon Souk. Now the dreams are quiet, but the silence is... loud.",
    "Childrens Fable": "Barnaby the beetle had a very important coat with seven pockets. In the first pocket, he kept a crumb of sugar for emergencies. In the second, a dewdrop for when he was thirsty. But the seventh pocket, the smallest one, was a secret. It held a tiny piece of the dark, just in case he ever grew tired of the light.",
    "Impossible Product Description": 'Product: Anti-Procrastination Stone. Hand-quarried from the Temporal Mines of Regret. This handsome, palm-sized stone gently emits a low-frequency temporal wave, making "later" feel like "right now." Ideal for filing taxes, writing novels, or finally confronting existential dread. (Warning: May cause spontaneous productivity. Do not lick the stone.)',
    "Minimalist Shopping List": "- eggs\n- wire\n- batteries (AAA)\n- lime\n- shovel\n- plastic sheeting",
    "Academic Abstract": 'This paper contests the prevailing historiographical interpretation of the "Great Silence" of the 14th century. While traditional scholarship attributes the sudden cessation of inter-continental trade to plague and famine, this analysis posits, through a re-examination of maritime logbooks and recently unearthed financial ledgers, that the cause was not terrestrial, but rather the abrupt and inexplicable disappearance of the North Star.',
    "Hardboiled Detective": "The dame had eyes you could drown in and a story with more holes than a block of cheap swiss. She said her husband, a big-shot inventor, had vanished. Left nothing behind but a lingering scent of ozone and a single, perfectly spherical hole burned through his laboratory wall. Trouble was my business, and business was booming.",
    "Age of Sail Log": "October 12th, 1788. Becalmed now for a fortnight. The sea is a plate of glass. The men are listless, and the whispers of a curse have turned to open talk. Cook swears he saw a face in the water yesterday, smiling up at him. I have ordered double rations of grog, more for my own nerves than for theirs. The water barrels are running low.",
    "Dystopian Propaganda": "A message from your Benefactors! Rejoice, citizens! The Thought-Purity initiative has been a glorious success. Crime is at an all-time low, and productivity has surged by 12%. Remember: A happy thought is a correct thought. Report any instances of irony or melancholy to your nearest Compliance Officer.",
    "Scientific Field Notes": "Specimen 734: Nocturnal Crystalline Fungus (crystallus somnus). Found only in deep cave systems. Appears inert during waking hours. Bioluminesces when exposed to human REM-sleep brainwaves. Light patterns seem to correspond to dreamer's emotional state. Hypothesis: the fungus feeds on dreams. Need to secure funding for EEG-integrated analysis.",
    "Resignation Email": "Subject: So Long, and Thanks for All the Fish\n\nDear Team,\nPlease accept this email as my official resignation. I have decided to pursue my lifelong dream of becoming a professional hermit. My two weeks' notice begins now, though my engagement with assigned tasks has, arguably, been on notice for some time. I wish you all the best in synergizing your deliverables.\nSigning off,\nDave",
    "Eldritch Recipe": "The Wanderer's Woe (Serves: 1, for a very long time). Take one memory, preferably of a lost love, and reduce it over a low flame of regret until it thickens. Add a pinch of starlight, three tears of a forgotten god, and a whisper of what might have been. Stir with a shard of obsidian. The concoction is ready when it begins to stare back at you.",
    "Western Tall Tale": "Old Man Hemlock, he was so tough he used to floss his teeth with barbed wire and use a rattlesnake for a necktie. One time, a tornado came through his property. He just stood on his porch, glared at it, and the durn thing got so scared it turned around and tied itself into a knot.",
    "Found Graffiti": "The universe is a joke, but the punchline is in a language you don't speak.",
    # Claude:
    "Mystery": "Detective Harding stared at the chalk outline. Everything seemed normal, except for the single playing card—the Queen of Spades—left in the victim's hand.",
    "NoirMystery": "The dame walked into my office at 2 AM, rain dripping from her fedora. She had trouble written in the curve of her smile and a revolver in her purse.",
    "CozyMystery": "Mrs. Pennywhistle's prized petunias had been mysteriously rearranged to spell 'GUILTY' in the village square garden.",
    "Sci-Fi": "The ship's AI, HAL-9001, spoke with an unnerving calm. 'I'm afraid the cryogenic pods have been... misplaced.'",
    "SpaceOpera": "The Galactic Council meeting was interrupted when Ambassador Zyx'theta's translation matrix began outputting only haikus.",
    "Cyberpunk": "She jacked into the mainframe, tasting copper and ozone as the data stream flooded her neural implants. Error code 404: Reality not found.",
    "TimeTravel": "The chronometer read Tuesday, but the newspaper said Thursday, and the sun was setting in the north.",
    "Fable": "In a forest where the rivers flowed with honey, there lived a badger who had forgotten how to laugh.",
    "HighFantasy": "The prophecy was clear: when the three moons align, a child born of silicon and starlight shall unite the warring kingdoms of flesh and circuit.",
    "UrbanFantasy": "The subway map had changed overnight. Station names like 'Grand Central' were replaced with 'The Goblin Market' and 'Dragon's Den.'",
    "FairyTale": "Once upon a time, in a kingdom made entirely of clockwork, there lived a princess who could only speak in mathematical equations.",
    "CosmicHorror": "The excavation team found it buried beneath the Antarctic ice: a door that opened inward from both sides.",
    "GothicHorror": "The portrait in the attic aged backwards, growing younger each night while the house's foundations grew teeth.",
    "BodyHorror": "Day 3: The rash has started forming letters. They spell out recipes I've never heard of, using ingredients I can't pronounce.",
    "StreamOfConsciousness": "Coffee cold again third cup today mother would say wasteful but the ceramic holds memories better than my hands these days wrinkled now like her maps of Venice never visited",
    "Minimalist": "She left. The door closed. The cat remained.",
    "MagicalRealism": "Every Thursday at 3:17 PM, gravity in the insurance office reversed for exactly twelve seconds. The employees had learned to secure their coffee cups.",
    "AcademicPaper": "Abstract: This study examines the correlation between sock disappearance rates in laundromats and local magnetic field fluctuations (n=2,847).",
    "NewsArticle": "BREAKING: Local man discovers his houseplant has been writing his emails for the past six months. Productivity reportedly up 340%.",
    "TravelGuide": "Chapter 7: Navigating the Non-Euclidean Geometry of Prague's Metro System. Pack extra dimensions.",
    "TechnicalManual": "WARNING: Do not operate the Temporal Displacement Unit while experiencing déjà vu. Do not operate the Temporal Displacement Unit while experiencing déjà vu.",
    "RecipeGone Wrong": "Interdimensional Soufflé (Serves 3-∞): Begin by preheating your oven to 350°F in at least four parallel universes.",
    "IkeaInstructions": "Step 1: Insert tab Ä into slot Ö while chanting the ancient names. If furniture begins levitating, proceed to step 2. If not, you have angered it.",
    "GroceryList": "Milk (2%), Eggs (chicken), Eggs (dragon), Bread (whole wheat), Bread (partially phased), Soap (existential), Cookies (chocolate chip), Portal stabilizer, Bananas",
    "OfficeEmail": "Re: Re: Re: Fwd: Urgent - The Coffee Machine Has Achieved Sentience. Hi all, Just a reminder to please stop feeding the coffee machine after midnight. -Janet from HR",
    "LegalDocument": "WHEREAS the party of the first part (hereinafter 'The Dreamer') did willfully and with malice aforethought imagine the party of the second part (hereinafter 'The Nightmare') into being,",
    "TaxForm": "Line 42a: Enter your total metaphysical income from Schedule J. If you existed in multiple dimensions simultaneously, see Form 1040-MD.",
    "CourtroomTranscript": "JUDGE: Let the record show the witness is a sentient fungal colony. DEFENSE: Objection! My client identifies as a symbiotic collective. JUDGE: Sustained. The court apologizes to all spores present.",
    "TherapySession": "THERAPIST: How does it make you feel when your shadow acts independently? PATIENT: Honestly, I'm just glad someone's taking initiative around here.",
    "CustomerService": "SUPPORT: Have you tried turning your reality off and on again? CALLER: Yes, but now everything tastes purple. SUPPORT: Ah, common issue. Let me escalate this to our Sensory Crosswiring Department.",
    "VictorianDiary": "15th May, 1887 - Most peculiar. The butler has begun speaking exclusively in prime numbers. Cook insists it's contagious. Have quarantined the kitchen staff as a precaution.",
    "MedievalChronicle": "In the year of our Lord 1347, the village of Little Wickshire did report that their church bell had begun ringing sideways, causing time to puddle in the town square.",
    "FutureLingo": "Chrono-log 2847.3: Biomass designation 'Jenkins' has exceed recommended nostalgia quotient. Prescribing immediate de-memorification protocols.",
    "ConcretePoetry": "The words.       fell.           like.                    rain.                              upward.                                        into.                                                  yesterday.",
    "ListPoem": "Things found in grandmother's attic: 1. Dust from the moon landing 2. A jar of Wednesday 3. Father's unused words 4. A map to somewhere that isn't",
    "Palindrome": "A man, a plan, a canal: Panama. But in the mirror universe: amanaP :lanac a ,nalp a ,nam A. Both canals led nowhere.",
    "WesternSciFi": "The asteroid prospector adjusted his space spurs. 'This here nebula ain't big enough for the both of us, you dad-blamed alien varmint.'",
    "RomanceHorror": "His eyes smoldered with passion. Also, they were literally on fire. This was becoming a recurring problem in their relationship.",
    "HistoricalFantasy": "Napoleon's defeat at Waterloo was not due to military tactics, but rather his army's unicorns going on strike for better working conditions.",
    "KafkaesqueBureaucracy": "Form 27B required Form 33C, which could only be obtained with Form 27B. The clerk smiled helpfully as reality folded in on itself.",
    "SurrealSliceOfLife": "Margaret's Tuesday routine: Wake up, brush teeth, have coffee, discover she's been a swarm of bees all along, drive to work.",
    "DadaistNews": "Local weather: Expect heavy showers of punctuation marks in the morning, clearing to a light drizzle of umlauts by afternoon. Winds from the conceptual northeast.",
    "CorruptedNurseryRhyme": "Humpty Dumpty sat on a wall, Humpty Dumpty had a great fall. All the king's horses and all the king's men, Couldn't explain why the wall was now inside Humpty instead.",
    "DarkChildrensBook": "The Very Hungry Caterpillar woke up on Monday and ate through one apple, one universe, and the concept of linear time.",
    "MetaNarrative": "This is the story of a story that refused to begin. Every time someone tried to read it, it would skip ahead to its own ending, which hadn't been written yet.",
    "FourthWallBreaking": "Chapter 1: The protagonist looked directly at you. Yes, you, holding this text. 'We need to talk about your reading habits,' she said.",
    "WikipediaEntry": "The Great Emu War (1932) was a military operation in Australia. [citation needed] The emus won. [citation desperately needed] They now control Parliament. [source: trust me]",
    "AmazonReview": "⭐⭐⭐ Stars out of 5 - Product arrived as described but opened a portal to the Nth dimension in my kitchen. Shipping was fast though.",
    "RedditPost": "TIFU by accidentally inverting the local flow of causality. Now my coffee makes me, and I have to drink my job every morning. Edit: Thanks for the gold, kind time-traveler!",
    "MedicalChart": "Patient presents with chronic existentialism and acute awareness of the void. Prescribed 20mg of denial twice daily. Side effects may include enlightenment.",
    "PoliceReport": "Incident #8834: Suspect claims to be 'unstuck in time.' Witness reports seeing suspect at crime scene, childhood home, and deathbed simultaneously.",
    "RestaurantMenu": "Today's Special: Deconstructed Reality Salad - Fresh concepts tossed with aged paradoxes, served on a bed of shredded expectations. Market price (varies by dimension).",
    "PhilosophicalTreatise": "If a tree falls in a forest and no one is around to hear it, does it make a sound? Follow-up question: What if the tree is the one asking?",
    "ReligiousText": "Book of Uncertainties 3:14 - 'And lo, the Prophet did speak: The divine plan is written in Comic Sans, and none may read it without weeping.'",
    "SportsCommentary": "And here comes Johnson with the ball! He passes to himself from yesterday, dodges the existential defender, and—OH MY—he's scored in the wrong universe!",
    "ChessNotation": "1. e4 e5 2. Nf3 Nc6 3. Bishop transcends physical plane 4. Black resigns due to cosmic horror",
    "TextMessages": "Mom (3:14 PM): Hi sweetie! Your father has become one with the dishwasher again. Should I call the shaman or the plumber? Love you!",
    "VoicemailTranscript": "You have... SEVENTEEN... new messages. First message: 'Hi, this is your future self. Don't answer this call.' End of message.",
    "LanguageLesson": "Lesson 12: Conjugating Verbs in the Subjunctive Past-Future Tense. Example: 'I will have might have been going to be.' Practice with your temporal grammar buddy.",
    "CookingShow": "Next, we'll add a pinch of entropy to taste. If your sauce begins questioning its own existence, you've added too much. Simply stir counterchronologically until stable.",
    "FieldNotes": "Day 47: The migrating geese are flying in Möbius strips again. This is the third flock this week. Suspect magnetic field has developed opinions.",
    "WeatherReport": "Tonight's forecast: Dark, with widely scattered light in the morning. Chance of existence: 74%. Winds from all directions simultaneously.",
    "MovieReview": "★★★★☆ - The film's third act boldly takes place during the first act. Director claims this was intentional. Audience members are advised to watch in random order.",
    "ConcertSetlist": "1. Opening Silence (Extended Mix) 2. The Sound of One Hand Clapping (Acoustic) 3. Intermission (Performed Twice) 4. Encore (Performed First)",
    "FortueCookie": "Your lucky numbers are: i, π², -∞, purple, and the sound of one hand clapping. Also, help, I'm trapped in a fortune cookie factory.",
    "CaptchaPrompt": "Please prove you're human by selecting all squares containing the concept of 'regret' or 'things that could have been.'",
    "ErrorMessage": "Error 404: Reality not found. Would you like to: [Create New Reality] [Use Cached Reality] [Continue Without Reality]?",
    "ShampooBottle": "Directions: Lather, rinse, repeat until you achieve enlightenment or run out of hot water, whichever comes first. Not tested on animals (they knew better).",
}

PARAM_RANGES = {
    "temperature": (0.7, 1.3),
    "top_p": (0.8, 1.0),
    "top_k": (20, 100),
    "typical_p": (0.2, 0.95),
    "repetition_penalty": (1.0, 1.3),
    "encoder_repetition_penalty": (1.0, 1.2),
    "no_repeat_ngram_size": [0, 2, 3],
    "min_new_tokens": (30, 80),
    "max_new_tokens": (100, 250),
}


class JudgeGenerator(TextGenerator):
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def generate_text(self, max_length: int | None = None) -> str:
        chosen_narrative = random.choice(list(NARRATIVE_SEEDS.keys()))
        priming_text = NARRATIVE_SEEDS[chosen_narrative]

        params = {}
        # Use nucleus/typical sampling only.
        use_typical_p = random.choice([True, False])
        if use_typical_p:
            params["typical_p"] = random.uniform(*PARAM_RANGES["typical_p"])
        else:
            params["top_p"] = random.uniform(*PARAM_RANGES["top_p"])

        params.update(
            {
                "temperature": random.uniform(*PARAM_RANGES["temperature"]),
                "top_k": random.randint(
                    int(PARAM_RANGES["top_k"][0]), int(PARAM_RANGES["top_k"][1])
                ),
                "do_sample": True,
            }
        )

        params.update(
            {
                "repetition_penalty": random.uniform(
                    *PARAM_RANGES["repetition_penalty"]
                ),
                "encoder_repetition_penalty": random.uniform(
                    *PARAM_RANGES["encoder_repetition_penalty"]
                ),
                "no_repeat_ngram_size": random.choice(
                    PARAM_RANGES["no_repeat_ngram_size"]
                ),
            }
        )

        min_tokens = random.randint(
            int(PARAM_RANGES["min_new_tokens"][0]),
            int(PARAM_RANGES["min_new_tokens"][1]),
        )
        max_tokens = (
            max_length
            if max_length is not None
            else random.randint(
                int(PARAM_RANGES["max_new_tokens"][0]),
                int(PARAM_RANGES["max_new_tokens"][1]),
            )
        )
        if min_tokens >= max_tokens:
            min_tokens = max_tokens - 1
        params["min_new_tokens"] = min_tokens
        params["max_new_tokens"] = max_tokens

        inputs = self.tokenizer(priming_text, return_tensors="pt").to(self.model.device)

        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs, **params, pad_token_id=self.tokenizer.eos_token_id
            )

        generated_completion = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )
        return generated_completion

    def generate_list(self, prompt: str, length: int) -> list[str]:
        # Build a robust, generic list-format priming prompt with sentinels.
        example_colors = (
            "Make a diverse list that matches the query.\n"
            "Query: colors\n"
            "Output rules:\n"
            "- One item per line\n"
            "- No numbering, no extra text\n"
            "- Avoid duplicates and close paraphrases\n"
            "BEGIN LIST\n"
            "red\n"
            "blue\n"
            "chartreuse\n"
            "ultramarine\n"
            "puce\n"
            "END LIST\n\n"
        )
        example_sentences = (
            "Make a diverse list that matches the query.\n"
            "Query: sentences with at least three clauses\n"
            "Output rules:\n"
            "- One item per line\n"
            "- No numbering, no extra text\n"
            "- Aim for sentences with multiple clauses\n"
            "- Avoid duplicates and close paraphrases\n"
            "BEGIN LIST\n"
            "When the bell rang, I grabbed my bag, and I ran to the gate.\n"
            "Although the sky darkened, we kept walking, and we found shelter near the bridge.\n"
            "Because the engine sputtered, the car slowed, but we still made it home.\n"
            "END LIST\n\n"
        )

        base_header = (
            "Make a diverse list that matches the query.\n"
            f"Query: {prompt}\n"
            "Output rules:\n"
            "- One item per line\n"
            "- No numbering, no extra text\n"
            "- Avoid duplicates and close paraphrases\n"
        )

        priming_prefix = example_colors + example_sentences + base_header

        def _build_prompt(accumulated: list[str]) -> str:
            prompt_text = priming_prefix
            if accumulated:
                # Include a compact avoid list to encourage diversity.
                # Limit to a reasonable number to keep prompt short.
                avoid_list = ", ".join(accumulated[:32])
                prompt_text += f"Avoid duplicates: {avoid_list}\n"
            prompt_text += "BEGIN LIST\n"
            return prompt_text

        def _choose_params(max_new: int, min_new: int) -> dict:
            params: dict[str, object] = {}
            # Use nucleus or typical sampling (as in generate_text).
            use_typical_p = random.choice([True, False])
            if use_typical_p:
                params["typical_p"] = random.uniform(*PARAM_RANGES["typical_p"])  # type: ignore[index]
            else:
                params["top_p"] = random.uniform(*PARAM_RANGES["top_p"])  # type: ignore[index]

            params.update(
                {
                    "temperature": random.uniform(*PARAM_RANGES["temperature"]),  # type: ignore[index]
                    "top_k": random.randint(
                        int(PARAM_RANGES["top_k"][0]),
                        int(PARAM_RANGES["top_k"][1]),  # type: ignore[index]
                    ),
                    "do_sample": True,
                }
            )

            params.update(
                {
                    "repetition_penalty": random.uniform(
                        *PARAM_RANGES["repetition_penalty"]  # type: ignore[index]
                    ),
                    "encoder_repetition_penalty": random.uniform(
                        *PARAM_RANGES["encoder_repetition_penalty"]  # type: ignore[index]
                    ),
                    "no_repeat_ngram_size": random.choice(
                        PARAM_RANGES["no_repeat_ngram_size"]  # type: ignore[index]
                    ),
                    "min_new_tokens": max(1, min_new),
                    "max_new_tokens": max(2, max_new),
                }
            )
            return params

        def _parse_lines(generated: str) -> list[str]:
            lines = []
            for raw in generated.splitlines():
                text = raw.strip()
                if not text:
                    continue
                if text.upper().startswith("END LIST"):
                    break
                # Robust against model echoing headers or bullets/numbers.
                if (
                    text.startswith("Make a diverse list")
                    or text.startswith("Output rules:")
                    or text.startswith("Query:")
                ):
                    continue
                # Trim common list markers and quotes.
                while text and text[0] in "-*•\u2022":
                    text = text[1:].lstrip()
                if text and text[0] in "\"'" and text[-1:] in "\"'" and len(text) > 1:
                    text = text[1:-1].strip()
                # Remove leading numbering like "1." or "2)".
                i = 0
                while i < len(text) and text[i].isdigit():
                    i += 1
                if i < len(text) and i > 0 and text[i : i + 1] in ".)":
                    text = text[i + 1 :].lstrip()
                if text and text.upper() != "BEGIN LIST":
                    lines.append(text)
            return lines

        collected: list[str] = []
        seen_norm: set[str] = set()

        def _maybe_add(items: list[str]) -> None:
            for item in items:
                norm = " ".join(item.strip().split()).casefold()
                if not norm:
                    continue
                if norm in seen_norm:
                    continue
                seen_norm.add(norm)
                collected.append(item)
                if len(collected) >= length:
                    return

        max_passes = 4
        for _ in range(max_passes):
            if len(collected) >= length:
                break

            priming_text = _build_prompt(collected)

            # Token budget targeting: aim for several items per pass.
            target = max(60, min(12 * max(1, length - len(collected)), 256))
            min_new = min(target - 1, max(20, target // 2))
            params = _choose_params(max_new=target, min_new=min_new)

            print("Priming text:")
            print(priming_text)
            inputs = self.tokenizer(priming_text, return_tensors="pt").to(
                self.model.device
            )
            with torch.inference_mode():
                outputs = self.model.generate(
                    **inputs, **params, pad_token_id=self.tokenizer.eos_token_id
                )
            continuation = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
            )

            items = _parse_lines(continuation)
            _maybe_add(items)

        return collected[:length]
