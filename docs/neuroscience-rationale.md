# The neuroscience behind Motor & Facial N-Back

*Why watching a move, holding it in mind while new ones arrive, and performing it later is a meaningful thing to
train, what the evidence says it can and cannot do, and how each design choice of the app follows from it.*

> **Status of this document.** This is a narrative review written to explain the app's design, not a
> systematic review. The references are well-known primary papers and reviews, but they were cited from
> knowledge rather than re-checked one by one for this text: check a reference before you cite it in your own
> work. Where the evidence is weak, contested or simply absent, the text says so. Nothing here is a medical
> claim. The app is a training tool, not a treatment.

---

## Contents

1. [Summary](#1-summary)
2. [What one trial asks of the brain](#2-what-one-trial-asks-of-the-brain)
3. [Motor and kinesthetic working memory](#3-motor-and-kinesthetic-working-memory)
4. [Updating: the core of the n-back](#4-updating-the-core-of-the-n-back)
5. [From observation to motor memory, and retrieving it](#5-from-observation-to-motor-memory-and-retrieving-it)
6. [The action-observation ("mirror") system and its trainability](#6-the-action-observation-mirror-system-and-its-trainability)
7. [Sport: observation, imagery and anticipation](#7-sport-observation-imagery-and-anticipation)
8. [Faces: mimicry, expression and social cognition](#8-faces-mimicry-expression-and-social-cognition)
9. [Autism and the "broken mirror": a careful note](#9-autism-and-the-broken-mirror-a-careful-note)
10. [Transfer: what training can reasonably be expected to change](#10-transfer-what-training-can-reasonably-be-expected-to-change)
11. [Design choices and their rationale](#11-design-choices-and-their-rationale)
12. [Evaluating your own progress honestly](#12-evaluating-your-own-progress-honestly)
13. [Limitations and open questions](#13-limitations-and-open-questions)
14. [References](#14-references)

---

## 1. Summary

The classic n-back task (Kirchner, 1958) shows a stream of items and asks, for each one, whether it matches the
item *n* positions back. It is one of the most used probes of working memory in neuroimaging and reliably
recruits a fronto-parietal network (Owen et al., 2005). Almost all n-back research uses letters, digits,
locations or sounds, and a button press as the answer.

Motor & Facial N-Back changes two things:

- **The content is a body movement or a facial expression.** The items are actions of the human body, shown by
  a 3D figure or a stylised face.
- **The answer is to perform the item.** You do not press "match"; you reproduce, with your own body or face,
  the move shown *n* trials earlier, while watching a new one.

These two changes bring in systems that the letter n-back does not need:

- **Body-based working memory.** There is good behavioural evidence for a store for movements and body
  configurations that is partly separate from visuo-spatial memory (Smyth & Pendleton, 1989, 1990).
- **The action-observation network.** Premotor, parietal and temporal regions are active both when we watch an
  action and when we do it. This is the human "mirror" system (Rizzolatti & Craighero, 2004).
- **Imitation and motor memory.** Observation alone can leave a trace in the motor system (Stefan et al., 2005;
  Mattar & Gribble, 2005). Performing from memory is an act of retrieval, and retrieval itself strengthens
  memory (Roediger & Karpicke, 2006).
- **For faces, sensorimotor simulation.** Producing and recognising expressions share mechanisms (Wood et al.,
  2016), and facial mimicry plays a role in social interaction (Hess & Fischer, 2013).

The honest expectation is as follows:

- **Within the task:** what is very likely to improve is the trained ability itself. That means holding and
  updating body movements and expressions in mind, reproducing them accurately, and building a larger
  "vocabulary" of moves you can encode quickly.
- **Near transfer:** to imitation, learning choreography or combinations, reading and copying movements in
  sport. This is plausible and has partial support from the motor-learning and expertise literatures. It has
  not been shown for this specific task.
- **Far transfer:** to general intelligence, everyday memory or social skills. The broader working-memory
  training literature gives no reason to expect it (Melby-Lervåg & Hulme, 2013; Sala & Gobet, 2019; Simons et
  al., 2016).

---

## 2. What one trial asks of the brain

Take a 2-back block. On trial *t* the figure plays move *M(t)*. You are asked to perform *M(t−2)* while *M(t)*
is still being encoded and *M(t−1)* must be kept for the next trial. Broken into processes, one trial needs:

| Step | Process | Main systems involved (simplified) |
|---|---|---|
| 1 | **Perceive** the new move: body form and kinematics | Occipito-temporal body areas (EBA), superior temporal sulcus for biological motion (Downing et al., 2001; Johansson, 1973) |
| 2 | **Map** it onto your own body: which limb, which side, which direction | Parietal and premotor action-observation network (Caspers et al., 2010) |
| 3 | **Encode** it into working memory as a body/motor code, often with a verbal label ("jab, cross") | Body-based working memory; phonological loop for labels (Smyth & Pendleton, 1989; Baddeley, 2000) |
| 4 | **Update** the set: drop the oldest item, shift positions, bind the new one to its position | Executive updating (Miyake et al., 2000); fronto-parietal cortex (Owen et al., 2005) |
| 5 | **Retrieve** the item *n* back, resisting the more recent ones (interference) | Interference control (Kane et al., 2007; Gray et al., 2003) |
| 6 | **Transform** it if asked (switch sides, a different viewpoint) | Mental body transformation (Parsons, 1987) |
| 7 | **Plan and execute** the movement or expression, then **monitor** it | Premotor and motor cortex, cerebellum; proprioceptive feedback |

Each step can fail on its own, and the report shows several of these failures separately:

- **Wrong item (intrusion).** You performed a move that was shown, but at the wrong position. The scoring
  compares your response with the recently shown items (`lure_items` in `mfnb/nback/plan.py`) and reports the
  confusion. Failures in steps 4–5 show up this way.
- **Right item, poor execution.** Step 7 failed, or the move was encoded imprecisely (step 3).
- **Wrong side.** A mirroring or laterality error (steps 2 and 6).

This decomposition is why the app is not "just" a memory game. Steps 2, 6 and 7 are the ones a letter n-back
never asks for.

---

## 3. Motor and kinesthetic working memory

### 3.1 A memory for movements

Baddeley and Hitch's (1974) model split working memory into a phonological loop, a visuo-spatial sketchpad and
a central executive. A later addition was the episodic buffer, which binds information across codes (Baddeley,
2000). Movements of the body did not fit cleanly into any of these, and a line of work in the late 1980s asked
whether they need a store of their own.

- **Smyth, Pearson and Pendleton (1988)** compared memory for sequences of body movements with memory for
  sequences of spatial locations (the Corsi blocks).
- **Smyth and Pendleton (1989, 1990)** developed this into a **dissociation**:
  - Memory span for meaningless body movements is roughly four items.
  - It is disrupted by performing other, unrelated movements during retention.
  - It is much less disrupted by spatial tapping.
  - The pattern for spatial (Corsi) span is the reverse.

  The authors argued for a movement-specific component of working memory, coding body configurations rather
  than positions in external space.
- **Woodin and Heil (1996)** found that skilled rowers' movement memory was linked to their performance. This
  suggests that body-pattern memory matters for skill, not only in the lab.
- **Wood (2007)** showed that visual working memory for *observed* actions has its own capacity limit. It
  behaves as a separate pool from memory for colours or shapes.
- **Gálvez-Pol and colleagues** later showed that holding images of bodies in visual working memory engages
  somatosensory and motor cortex. They reviewed this line of work in Gálvez-Pol, Forster and Calvo-Merino
  (2020). On this view, part of the storage is done by the systems that represent the body.

In short: there is a reasonable case for a working-memory resource for body configurations and movements. It is
partly separable from visuo-spatial and verbal memory, and it is grounded in sensorimotor regions. The exact
architecture (a separate "kinesthetic store" or embodied re-use of sensorimotor areas) is still debated.

### 3.2 Kinesthetic versus visual codes

When you watch the figure, the move first arrives as a **visual** code (what it looks like). When you perform
it, you need a **motor or kinesthetic** code (what it feels like and how to make it). People can hold either.
Which one they use changes what interferes with it:

- **Visual code:** watching a new move while holding an old one is mainly a visual interference problem.
- **Motor code:** if the old move has been "rehearsed" as a motor plan, performing a different move interferes
  with it. This is the effect Smyth and Pendleton relied on.

The n-back puts both kinds of interference in the same trial: you watch one move and perform another. That is
part of what makes it hard, and part of what it trains.

### 3.3 Enactment and labels

Memory research on **enactment** shows that actions you have performed are remembered better than actions you
only heard about or watched (Engelkamp, 1998). The motor component adds a distinct, durable trace.

Many people also attach **verbal labels** to moves ("jab, cross, hook" or "left knee up"). This recruits the
phonological loop and frees body-based capacity. Experts do this systematically. The app does not forbid it:

- With familiar moves, labels are an efficient strategy, and they are how real-world skills are coded.
- With **unfamiliar** moves (complexity 4–5, unusual combinations), labels fail, and you must rely on body
  codes. Mixing both kinds keeps the body-based component in play.

---

## 4. Updating: the core of the n-back

### 4.1 Updating as an executive function

Miyake et al. (2000) showed that executive functions are partly unitary and partly distinct. Their three
factors were shifting, inhibition and **updating**. Updating means monitoring incoming information and replacing
old content with more relevant content. The n-back is one of the standard updating tasks.

Each trial requires three operations:

1. **Remove** the item that has become irrelevant.
2. **Add** the new one.
3. **Re-bind** every item to its new position ("this was 1-back, now it is 2-back").

The binding of item to position is the expensive part. Oberauer's (2002) work on the focus of attention suggests
that only one item at a time is in a privileged, directly accessible state. Moving between the stored items
takes time and is error-prone.

### 4.2 Interference and lures

**Lures** are items that match at the wrong distance, for example a move that appeared 1 or 3 back in a 2-back
block. In the letter n-back, lure trials are where the task taps interference control most directly. They
correlate with fluid intelligence and engage lateral prefrontal cortex (Gray et al., 2003).

Kane et al. (2007) showed that n-back performance correlates only weakly with complex-span measures of working
memory. Interference resolution and familiarity-based responding explain part of the difference. In other
words, the n-back is not a pure "capacity" measure. A good part of what it measures is resisting recent, familiar
items.

In Motor & Facial N-Back, every trial is in a sense a lure trial. The other recently shown moves are always
present in memory, and the scoring checks your response against them. The report tells you whether a miss was
an intrusion of the move from N−1 or N+1. In the n-back literature these errors are the main signature of
updating and interference failures.

### 4.3 Making updating harder in principled ways

The app offers optional twists. Each one loads a specific process:

- **Variable N** (N ± 1 on some trials). The position to retrieve is announced trial by trial, so you cannot
  settle into a fixed "pipeline" and must keep position bindings precise.
- **Switch sides** (perform the mirror image). This adds a mental transformation of the body. Judgements about
  the laterality of a body part are made by mentally moving one's own body into the shown posture (Parsons,
  1987). The cost grows with the angle and the awkwardness of the transformation. Holding a move and converting
  it to the other side adds a manipulation step on top of maintenance. Maintenance plus manipulation is a
  classic way to increase prefrontal load.
- **Sequence mode** ("do N−2, then N"). This requires retrieving two positions in order. It loads serial order
  and resembles real combination drills.

### 4.4 Chunking and expertise

Experts hold far more in working memory than novices in their field. They do not have a larger store; they have
learned chunks and retrieval structures in long-term memory ("long-term working memory", Ericsson & Kintsch,
1995).

In motor learning, sequences become segmented into chunks with practice. Movements within a chunk run together,
and boundaries show up as pauses (Sakai, Kitaguchi & Hikosaka, 2003).

The library is built with this in mind:

- **Primitives and combinations.** Moves are primitives and combinations of increasing **complexity (1–5)**.
- **Familiar moves become chunks.** As you train, familiar moves become single chunks, so the effective load
  drops. That is why the adaptive N can rise.
- **Unfamiliar material keeps the task honest.** New and complex moves stop chunking from doing all the work.

---

## 5. From observation to motor memory, and retrieving it

### 5.1 Watching forms motor memories

Two classic experiments showed that observation alone changes the motor system:

- **Stefan et al. (2005).** Watching a video of thumb movements in one direction biased the direction of
  movements later evoked by transcranial magnetic stimulation (TMS) of motor cortex, toward the observed
  direction. This is the same kind of change produced by physically practising that movement. The authors
  called it the formation of a motor memory by observation.
- **Mattar and Gribble (2005).** Watching someone learn to reach in a novel force field improved the
  observers' own performance in that force field. Watching the opposite force field made it worse. The effect
  did not depend on explicit knowledge and survived a cognitive distraction task.

Both studies point the same way: encoding the move on screen is already motor practice, not only "looking".

### 5.2 Simulation: observation, imagery and execution share resources

Jeannerod (2001) proposed that observing, imagining and executing actions share a common neural simulation
mechanism. Meta-analyses of neuroimaging data support a large overlap in premotor and parietal regions across
the three, with imagery and execution sharing more subcortical and cerebellar regions than observation does
(Hardwick et al., 2018).

During the delay between seeing a move and performing it, holding it "ready to go" probably involves covert
simulation. It is close to motor imagery, guided by the visual memory of the move.

### 5.3 Retrieval as practice

Each response in the app is a **retrieval**: you do not copy the move while it is shown, you reproduce it from
memory after other moves have come in between. This has two well-documented effects:

- **The testing effect.** Retrieving information strengthens it more than restudying it (Roediger & Karpicke,
  2006). The best-known findings are from verbal material, but recall from memory, rather than copying with
  the model in view, is also the usual basis of motor learning by imitation.
- **Contextual interference.** Practising several skills in an interleaved order gives worse performance during
  practice but better retention and transfer than practising them in blocks (Shea & Morgan, 1979). The n-back
  interleaves by construction: each move is surrounded by others. The size of the effect for complex,
  real-world skills is debated (Wulf & Shea, 2002), but the direction is consistent.

### 5.4 Feedback timing

Knowledge of results given after every trial helps performance during practice but can harm retention. People
come to depend on it (the "guidance hypothesis", Salmoni, Schmidt & Walter, 1984). The app therefore gives only
a brief colour flash after each response and keeps the detailed comparison (side-by-side replay) for the end of
the block.

### 5.5 Consolidation

Motor skills keep improving after practice ends, during **consolidation**. Sleep plays a role: performance on a
motor sequence task improved after a night of sleep but not after the same time awake (Walker et al., 2002). The
size and robustness of sleep-dependent gains have been questioned since, but spaced sessions across days remain
the safe recommendation. Several short sessions on different days are better than one long session.

---

## 6. The action-observation ("mirror") system and its trainability

### 6.1 What mirror neurons are

**Single neurons in the monkey.** In the early 1990s, recordings in macaque premotor area F5 found neurons that
fired both when the monkey performed a goal-directed hand action and when it watched the experimenter perform a
similar one (di Pellegrino et al., 1992). Similar neurons were later found in inferior parietal cortex.

**Evidence in humans.**

- **TMS.** Watching an action increases the excitability of the muscles that would perform it. The effect is
  muscle-specific (Fadiga et al., 1995).
- **Neuroimaging.** Observation and execution activate overlapping premotor and parietal regions (Caspers et
  al., 2010; Rizzolatti & Craighero, 2004).
- **Single neurons.** Rare recordings in epilepsy patients found single neurons with mirror properties in
  several regions, including the supplementary motor area and medial temporal lobe (Mukamel et al., 2010).

In this document, "mirror system" means this **action-observation network**. It is a set of regions with shared
coding for observed and executed actions, not a single type of cell.

### 6.2 What it is for: claims and critiques

**The strong claim.** The early view held that mirror neurons explain action understanding: we understand
others' actions by simulating them. They were later linked to imitation, intention reading, empathy and
language.

**The critiques.** Hickok (2009) listed problems with this view:

- Action understanding can survive damage to motor regions.
- Monkeys, who have mirror neurons, imitate poorly.
- The same responses could reflect association rather than understanding.

**The current view.** The network probably *contributes* to action perception. It is especially useful for
predicting the course and timing of actions (Kilner, Friston & Frith, 2007; Wolpert, Doya & Kawato, 2003). It
is not the sole basis of understanding others.

For this app, the weaker claim is enough. The task needs:

- precise mapping of seen movements onto one's own body;
- prediction of how a move unfolds;
- reproduction of the move.

These are exactly the functions the network is most clearly involved in.

### 6.3 It is trainable: the associative account

The most important finding for a training app is that the mirror system's matching properties are **learned**.
They are not fixed at birth.

- **Catmur, Walsh and Heyes (2007).** Before training, watching an index-finger movement selectively excited
  the index-finger muscle, and watching a little-finger movement excited the little-finger muscle. Participants
  then practised **incompatible** responses: moving the little finger when they saw an index-finger movement,
  and the reverse. After this, the TMS pattern **reversed**. A short period of sensorimotor training had
  reconfigured which motor representations observation activates.
- **Heyes (2010) and Cook et al. (2014).** These papers developed the **associative sequence learning**
  account. Mirror properties arise from correlated experience of seeing and doing: watching yourself move,
  being imitated, synchronising with others.
- **Expertise studies.**
  - Ballet and capoeira dancers showed stronger action-observation activity when watching their own style than
    the other style (Calvo-Merino et al., 2005).
  - Male and female ballet dancers responded more strongly to the gender-specific moves they had actually
    trained than to those they had only seen. Motor experience, not visual familiarity alone, mattered
    (Calvo-Merino et al., 2006).
  - Dancers learning new sequences over weeks showed growing premotor activity when watching those sequences
    (Cross, Hamilton & Grafton, 2006).

Three practical consequences follow for the app:

1. **Seeing and then doing builds the associations.** Watching a move and then performing it creates exactly
   the see–do pairing the associative account says builds mirror matching. Over many trials this should refine
   the mapping from seen bodies to one's own body. The effect is likely specific to the trained movement
   repertoire: the evidence is that matching is learned for the actions you practise.
2. **Mirror and anatomical mappings are different associations.**
   - People spontaneously imitate a person facing them **as a mirror** (raising the right hand when the model
     raises their left), and children imitate goals more than exact limbs (Bekkering, Wohlschläger & Gattis,
     2000).
   - Imitation shows an automatic compatibility effect: observed finger movements speed up the same movement
     and slow down a different one (Brass et al., 2000). Learning to override it is the inverse of the Catmur
     manipulation.
   - The app's view options (mirror, facing, from behind) and the switch-sides twist train these mappings
     separately. Left limbs in blue and right limbs in orange make the anatomical mapping explicit.
3. **Meaningless movements are especially useful.** Imitating meaningless gestures relies on a direct
   visuomotor route. Meaningful actions can be reproduced from stored knowledge of the action (Tessari &
   Rumiati, 2004). Patients with apraxia can show deficits in imitating meaningless postures, linked to a
   problem coding body-part relations (Goldenberg, 1995). The library's unusual combinations and static
   postures therefore load the body-mapping route more directly than well-known moves do.

### 6.4 Rehabilitation, as a pointer

"Action observation therapy" is used in stroke rehabilitation: patients watch daily actions and then practise
them. Ertelt et al. (2007) reported larger motor gains and increased activity in action-observation regions
compared with a control condition. Later trials and meta-analyses are generally positive but heterogeneous.
This is mentioned only to show that "watch, then do" is a recognised training principle. **This app is not
designed or validated for rehabilitation** and should not replace a therapist's programme.

---

## 7. Sport: observation, imagery and anticipation

### 7.1 Perceptual-cognitive expertise

Across sports, experts outperform novices in anticipating opponents' actions and recognising patterns, and they
do so with different eye movements (Mann et al., 2007).

Aglioti et al. (2008) showed that elite basketball players predicted the fate of free throws from the shooter's
body kinematics earlier and more accurately than expert watchers (coaches and journalists) with similar visual
experience. Their motor cortex excitability also changed specifically when watching shots that would miss.
Motor experience, not only visual experience, seems to support reading others' movements.

### 7.2 Observation plus imagery

Sport psychology uses both observation (watching a model or one's own video) and motor imagery (rehearsing a
move mentally).

- **Holmes and Calmels (2008)** reviewed the neuroscience behind both. They argued that techniques work best
  when the internal simulation is close to real execution in content, timing and perspective.
- **Combined use.** Observation and imagery can be used at the same time: imagining the felt movement while
  watching it. This combination tends to engage motor regions more than either alone (Vogt et al., 2013; Eaves
  et al., 2016).

In the app, the time between seeing a move and performing it is a natural slot for this kind of
"observe-then-imagine" rehearsal. The response window is generous so that execution can be complete rather than
rushed.

### 7.3 What it could mean for a combat-sport or dance practitioner

The library is rich in boxing, kicks, defence, grappling drills, taekwondo, karate, tai chi and dance. For a
practitioner, the task combines several skills:

- **Reading a demonstration once and reproducing it.** This is what a coach's "show then drill" requires.
- **Holding a combination while another is shown.** This is close to a partner calling the next combination
  while you are still executing the last one.
- **Switching sides and stances** (orthodox/southpaw, mirroring). This is a recognised training aim in many
  combat sports.

These are plausible routes of **near transfer**. They have not been tested for this app.

---

## 8. Faces: mimicry, expression and social cognition

### 8.1 Rapid facial mimicry

People tend to mimic the expressions they see. Facial EMG picks up small, fast responses: the smile muscle for
happy faces, the brow muscle for angry faces. These responses occur even when the faces are masked and not
consciously seen (Dimberg, Thunberg & Elmehed, 2000).

Mimicry is not a reflex copy, however. It depends on the relationship, the context and the meaning of the
expression (Hess & Fischer, 2013).

### 8.2 Simulation and recognition

According to simulation accounts, perceiving an expression partly re-activates the sensorimotor and affective
states of producing it, and this helps recognise its meaning (Niedenthal et al., 2010; Wood et al., 2016).
Supporting evidence:

- Blocking mimicry, for example by holding a pen in the mouth, can selectively impair recognition of the
  expressions that use those muscles (Oberman, Winkielman & Ramachandran, 2007).
- Amplifying facial feedback (with a restricting gel) can improve the perception of subtle expressions. Botox,
  which dampens it, can impair it (Neal & Chartrand, 2011).

Effects are generally small, and not all studies replicate.

### 8.3 The facial feedback debate

The stronger claim is that your expression changes your feelings, the "facial feedback hypothesis". Its history
illustrates why caution is needed:

- **Strack, Martin and Stepper (1988)** reported that holding a pen in a way that forced a smile made cartoons
  seem funnier.
- **A 17-lab registered replication** did not reproduce the effect (Wagenmakers et al., 2016).
- **A meta-analysis** of nearly 300 effects found a small but reliable overall effect (Coles, Larsen & Lench,
  2019).
- **The Many Smiles Collaboration** found evidence that posing smiles can slightly increase reported happiness
  (Coles et al., 2022). The results for the pen method were weaker.

The app does not rely on this hypothesis. It trains **voluntary control and memory for expressions**, and it
makes no claim that posing them changes mood.

### 8.4 Why train expressions?

Several reasons are reasonable, and none needs large claims:

- **Voluntary facial control is a skill.** Actors, speakers and people who want more expressive or more
  controlled faces train it. The library includes upper-face, lower-face, gaze and **asymmetric** actions,
  coded after the Facial Action Coding System (Ekman & Friesen, 1978). Asymmetric and isolated actions are hard
  for most people at first, and they improve with practice and feedback.
- **Fine-grained attention to faces.** To reproduce an expression from memory, you have to notice which parts
  moved. That is the same detail you need to perceive subtle expressions in others.
- **A memory load on expressions.** Holding several facial configurations in mind while new ones arrive is a
  distinct working-memory challenge, analogous to the motor version.

### 8.5 Social coordination

People unconsciously mimic the postures and mannerisms of those they interact with, and being mimicked
increases liking and smooths interaction (the "chameleon effect", Chartrand & Bargh, 1999). Moving in synchrony
with others also increases affiliation (Hove & Risen, 2009).

Since motor and facial coordination support social bonding, the skill of matching others' movements has social
value. **But** it would be an overreach to claim that a webcam game improves social skills. That is a far
transfer the evidence does not support (see §10).

### 8.6 Expressions are not emotions

The app names some expressions after emotions ("happy", "surprised"). This is a convenient label for a
configuration of facial actions, not a statement that the configuration *means* that emotion.

A major review concluded that the same emotion is expressed in many ways, and that the same configuration can
mean different things across people, contexts and cultures (Barrett et al., 2019). What the app trains is the
**movement**, not emotional insight.

---

## 9. Autism and the "broken mirror": a careful note

This section is included because the topic often comes up whenever mirror neurons are discussed, and it is
frequently presented badly.

**The original hypothesis.** The "broken mirror" hypothesis proposed that differences in imitation and social
cognition in autism come from a dysfunctional mirror system (Williams et al., 2001).

**What the evidence shows.** Systematic reviews found inconsistent support:

- Autistic people generally imitate goal-directed actions well.
- Differences appear more in spontaneous, automatic imitation and in the top-down control of when to imitate
  (Hamilton, 2013; Southgate & Hamilton, 2008).
- The "social top-down response modulation" (STORM) model places the difference in how social signals regulate
  mimicry rather than in the mirror system itself (Wang & Hamilton, 2012).
- Autistic children and adults can produce expressions voluntarily. Automatic mimicry may differ (McIntosh et
  al., 2006).

**The "double empathy problem".** Difficulties in social interaction between autistic and non-autistic people
are mutual, not a deficit located in one party (Milton, 2012). This perspective also shows that "training
mirrors to fix social skills" is a poor framing.

**Accordingly, this app makes no claims about autism.** An autistic person may use it, like anyone, for its
direct aims: movement memory, motor control, sport, dance, expression. Its purpose is not to "normalise"
anyone's social behaviour.

---

## 10. Transfer: what training can reasonably be expected to change

### 10.1 The working-memory training debate

**The early claim.** In 2008, Jaeggi and colleagues reported that training a dual n-back task (visual locations
plus spoken letters) improved fluid intelligence. The claim generated a large literature.

**The meta-analyses since then:**

- **Melby-Lervåg and Hulme (2013):** working-memory training produces reliable short-term gains on the trained
  and closely similar tasks. They found no convincing evidence of transfer to verbal ability, arithmetic,
  reading or reasoning.
- **Au et al. (2015):** a small positive effect of n-back training on fluid intelligence. It was sensitive to
  the type of control group, with larger effects against passive controls.
- **Soveri et al. (2017):** in a multilevel meta-analysis of n-back training, near transfer (other
  working-memory tasks) was small and far transfer negligible.
- **Sala and Gobet (2019):** across cognitive training domains, effects on general cognition shrink to about
  zero once study quality and placebo controls are taken into account.
- **Simons et al. (2016):** an extensive review of commercial "brain training" reached the same conclusion.
  Training improves trained tasks and little else.

**Why?** Gathercole et al. (2019) argued that working-memory training mainly teaches **new, task-specific
skills and strategies** (for example how to rehearse and how to chunk). These skills transfer only to tasks with
the same structure. The capacity of a general store does not change.

### 10.2 What this means here

The n-back literature is a reason **for modesty**, and also a guide to where benefits are realistic. The
following expectations follow from it.

**Very likely:** better performance on this task.

- Higher N, faster and more accurate reproduction of moves, fewer intrusions.
- A larger repertoire of moves you can encode as single chunks.

**Plausible (near transfer):** faster learning of choreography, combinations and drills, better imitation from
a single demonstration, better side-switching. These share structure with the task:

- they use the same content (body movements);
- they use the same processes (observing, mapping, holding, reproducing);
- the motor and expertise literatures support a link (§5–7).

**Not to be expected:** higher IQ, better memory for names or shopping lists, better social skills, or
treatment of any condition.

If the app has any advantage over a letter n-back, it is that **its content is itself useful**. The "task
specific" skills it builds are movements and expressions you may actually want to master.

### 10.3 Expectation and motivation

Training studies are vulnerable to placebo and expectation effects (Boot et al., 2013). People who believe a
training works try harder on post-tests. Keep this in mind when judging your own progress (§12).

---

## 11. Design choices and their rationale

| Design choice | Rationale | Key references |
|---|---|---|
| **Respond by performing** the item (not pressing "match") | Requires motor retrieval and execution; enactment strengthens memory; builds see–do associations | Engelkamp, 1998; Catmur et al., 2007; Stefan et al., 2005 |
| **First N trials watch-only** | Fills the memory set before the first response, as in the standard n-back | Kirchner, 1958 |
| **Adaptive N** (≥ 85% → N + 1, < 60% → N − 1) | Keeps the load near the limit, where training is most effective; the standard procedure in n-back training studies | Jaeggi et al., 2008 |
| **Response window 2–3× the stimulus** (default 2.5×) | Leaves time for full, accurate execution after retrieval; the goal is precise reproduction, not reaction speed | Holmes & Calmels, 2008 |
| **Intrusion analysis** (scoring against recently shown moves) | Separates updating/interference failures (wrong position) from execution failures | Kane et al., 2007; Gray et al., 2003 |
| **Variable N**, **sequence mode** | Prevents fixed "pipeline" strategies; loads position binding and serial order | Oberauer, 2002; Miyake et al., 2000 |
| **Switch sides** | Adds a mental body transformation to maintenance; trains anatomical vs mirror mapping | Parsons, 1987; Brass et al., 2000 |
| **Views: mirror / facing / from behind; side-view inset** | Different viewpoints need different body mappings; mirror imitation is spontaneous, anatomical is learned | Bekkering et al., 2000 |
| **Left limbs blue, right limbs orange** | Makes laterality explicit, reducing pure perceptual confusion so the memory load is the challenge | — |
| **Complexity 1–5, primitives and combinations** | Graded load; familiar moves become chunks, complex ones keep body codes in use | Sakai et al., 2003; Ericsson & Kintsch, 1995 |
| **Meaningless/static postures as well as known moves** | Load the direct visuomotor route of imitation | Tessari & Rumiati, 2004; Goldenberg, 1995 |
| **Interleaved categories** | Contextual interference: harder practice, better retention | Shea & Morgan, 1979 |
| **Discreet flash per trial; full report at the end** | Avoids dependence on immediate, detailed feedback | Salmoni et al., 1984 |
| **Sport and dance libraries** | Content with direct real-world value; supports near transfer | Calvo-Merino et al., 2005; Aglioti et al., 2008 |
| **Stance setting (orthodox/southpaw)** | Matches the repertoire to the user's real motor practice | Calvo-Merino et al., 2006 |
| **Facial library with isolated, asymmetric and gaze actions** | Trains voluntary control of individual facial actions, not only stereotyped "emotions" | Ekman & Friesen, 1978; Barrett et al., 2019 |
| **Personal neutral face at each facial block; face calibration** | Faces differ in shape and range of movement; scoring is relative to *your* face | — |
| **Body calibration, flexibility and space filters** | Scoring is relative to your body; moves you cannot or should not do are excluded | — |
| **Dashboard over days** | Spaced sessions and consolidation; visible progress supports motivation | Walker et al., 2002 |

---

## 12. Evaluating your own progress honestly

If you want to know whether training changes anything beyond the game, test it in a way that is hard to fool
yourself with:

1. **Pick an untrained outcome before you start.** Examples:
   - learning a new 8-count dance phrase or a new 6-move combination from one video viewing, then scoring how
     many elements you reproduce correctly;
   - copying a sequence of meaningless arm postures from a video.
   Use material that is **not** in the app.
2. **Measure it at the start**, then after several weeks of regular practice (for example, 15–20 minutes, 4–5
   times a week, for 4–6 weeks).
3. **Use parallel versions.** Use different but equally difficult sequences at each test, so you are not just
   relearning the first one.
4. **Compare with a control if you can.** A friend who practises the same amount of a different activity, or
   your own baseline period without training.
5. **Separate in-game progress from transfer.** Rising N is expected and is not by itself evidence of transfer.

The dashboard shows in-game progress. Only an outside test like this can show transfer.

---

## 13. Limitations and open questions

- **No direct validation.** The app combines established paradigms, but this specific task has not been tested
  in a controlled study. Its effects are inferred from related evidence.
- **Scoring is approximate.** Pose and face tracking from a single webcam are noisy:
  - depth is estimated;
  - small facial movements are near the tracker's resolution;
  - lighting and camera angle matter.
  Scoring therefore judges a move's shape and timing within tolerances, not its biomechanical quality.
- **The motor working-memory architecture is debated.** It is not settled whether there is a dedicated
  kinesthetic store or embodied use of sensorimotor areas. The training rationale does not depend on which
  answer is right.
- **Mirror-system accounts are partly contested** (§6.2). The design relies only on the well-supported parts:
  shared coding for observation and execution, and its plasticity with sensorimotor experience.
- **Strategies.** Verbal labels can carry much of the load for familiar moves. This is normal skill
  acquisition, but it means the "body-based" component is greatest for new and complex material.
- **Safety.** The app is not a medical device. Moves can be physically demanding; use the flexibility and space
  filters and stop if anything hurts.

Open questions that this kind of tool could help answer:

- Does motor n-back training improve one-shot imitation of new sequences more than a letter n-back does?
- Do switch-sides and viewpoint variations lead to more flexible body mapping?
- Is there any benefit for sport-specific anticipation in practitioners?

---

## 14. References

Aglioti, S. M., Cesari, P., Romani, M., & Urgesi, C. (2008). Action anticipation and motor resonance in elite
basketball players. *Nature Neuroscience, 11*(9), 1109–1116.

Au, J., Sheehan, E., Tsai, N., Duncan, G. J., Buschkuehl, M., & Jaeggi, S. M. (2015). Improving fluid
intelligence with training on working memory: A meta-analysis. *Psychonomic Bulletin & Review, 22*(2), 366–377.

Baddeley, A. (2000). The episodic buffer: A new component of working memory? *Trends in Cognitive Sciences,
4*(11), 417–423.

Baddeley, A. D., & Hitch, G. (1974). Working memory. In G. H. Bower (Ed.), *The Psychology of Learning and
Motivation* (Vol. 8, pp. 47–89). Academic Press.

Barrett, L. F., Adolphs, R., Marsella, S., Martinez, A. M., & Pollak, S. D. (2019). Emotional expressions
reconsidered: Challenges to inferring emotion from human facial movements. *Psychological Science in the Public
Interest, 20*(1), 1–68.

Bekkering, H., Wohlschläger, A., & Gattis, M. (2000). Imitation of gestures in children is goal-directed.
*Quarterly Journal of Experimental Psychology A, 53*(1), 153–164.

Boot, W. R., Simons, D. J., Stothart, C., & Stutts, C. (2013). The pervasive problem with placebos in psychology:
Why active control groups are not sufficient to rule out placebo effects. *Perspectives on Psychological Science,
8*(4), 445–454.

Brass, M., Bekkering, H., Wohlschläger, A., & Prinz, W. (2000). Compatibility between observed and executed
finger movements: Comparing symbolic, spatial, and imitative cues. *Brain and Cognition, 44*(2), 124–143.

Calvo-Merino, B., Glaser, D. E., Grèzes, J., Passingham, R. E., & Haggard, P. (2005). Action observation and
acquired motor skills: An fMRI study with expert dancers. *Cerebral Cortex, 15*(8), 1243–1249.

Calvo-Merino, B., Grèzes, J., Glaser, D. E., Passingham, R. E., & Haggard, P. (2006). Seeing or doing? Influence
of visual and motor familiarity in action observation. *Current Biology, 16*(19), 1905–1910.

Caspers, S., Zilles, K., Laird, A. R., & Eickhoff, S. B. (2010). ALE meta-analysis of action observation and
imitation in the human brain. *NeuroImage, 50*(3), 1148–1167.

Catmur, C., Walsh, V., & Heyes, C. (2007). Sensorimotor learning configures the human mirror system. *Current
Biology, 17*(17), 1527–1531.

Chartrand, T. L., & Bargh, J. A. (1999). The chameleon effect: The perception–behavior link and social
interaction. *Journal of Personality and Social Psychology, 76*(6), 893–910.

Coles, N. A., Larsen, J. T., & Lench, H. C. (2019). A meta-analysis of the facial feedback literature: Effects of
facial feedback on emotional experience are small and variable. *Psychological Bulletin, 145*(6), 610–651.

Coles, N. A., March, D. S., Marmolejo-Ramos, F., et al. (2022). A multi-lab test of the facial feedback hypothesis
by the Many Smiles Collaboration. *Nature Human Behaviour, 6*(12), 1731–1742.

Cook, R., Bird, G., Catmur, C., Press, C., & Heyes, C. (2014). Mirror neurons: From origin to function.
*Behavioral and Brain Sciences, 37*(2), 177–192.

Cross, E. S., Hamilton, A. F. de C., & Grafton, S. T. (2006). Building a motor simulation de novo: Observation of
dance by dancers. *NeuroImage, 31*(3), 1257–1267.

di Pellegrino, G., Fadiga, L., Fogassi, L., Gallese, V., & Rizzolatti, G. (1992). Understanding motor events: A
neurophysiological study. *Experimental Brain Research, 91*(1), 176–180.

Dimberg, U., Thunberg, M., & Elmehed, K. (2000). Unconscious facial reactions to emotional facial expressions.
*Psychological Science, 11*(1), 86–89.

Downing, P. E., Jiang, Y., Shuman, M., & Kanwisher, N. (2001). A cortical area selective for visual processing of
the human body. *Science, 293*(5539), 2470–2473.

Eaves, D. L., Riach, M., Holmes, P. S., & Wright, D. J. (2016). Motor imagery during action observation: A brief
review of evidence, theory and future research opportunities. *Frontiers in Neuroscience, 10*, 514.

Ekman, P., & Friesen, W. V. (1978). *Facial Action Coding System*. Consulting Psychologists Press.

Engelkamp, J. (1998). *Memory for Actions*. Psychology Press.

Ericsson, K. A., & Kintsch, W. (1995). Long-term working memory. *Psychological Review, 102*(2), 211–245.

Ertelt, D., Small, S., Solodkin, A., Dettmers, C., McNamara, A., Binkofski, F., & Buccino, G. (2007). Action
observation has a positive impact on rehabilitation of motor deficits after stroke. *NeuroImage, 36*(Suppl. 2),
T164–T173.

Fadiga, L., Fogassi, L., Pavesi, G., & Rizzolatti, G. (1995). Motor facilitation during action observation: A
magnetic stimulation study. *Journal of Neurophysiology, 73*(6), 2608–2611.

Gálvez-Pol, A., Forster, B., & Calvo-Merino, B. (2020). Beyond action observation: Neurobehavioral mechanisms of
memory for visually perceived bodies and actions. *Neuroscience & Biobehavioral Reviews, 116*, 508–518.

Gathercole, S. E., Dunning, D. L., Holmes, J., & Norris, D. (2019). Working memory training involves learning new
skills. *Journal of Memory and Language, 105*, 19–42.

Goldenberg, G. (1995). Imitating gestures and manipulating a mannikin: The representation of the human body in
ideomotor apraxia. *Neuropsychologia, 33*(1), 63–72.

Gray, J. R., Chabris, C. F., & Braver, T. S. (2003). Neural mechanisms of general fluid intelligence. *Nature
Neuroscience, 6*(3), 316–322.

Hamilton, A. F. de C. (2013). Reflecting on the mirror neuron system in autism: A systematic review of current
theories. *Developmental Cognitive Neuroscience, 3*, 91–105.

Hardwick, R. M., Caspers, S., Eickhoff, S. B., & Swinnen, S. P. (2018). Neural correlates of action: Comparing
meta-analyses of imagery, observation, and execution. *Neuroscience & Biobehavioral Reviews, 94*, 31–44.

Hess, U., & Fischer, A. (2013). Emotional mimicry as social regulation. *Personality and Social Psychology
Review, 17*(2), 142–157.

Heyes, C. (2010). Where do mirror neurons come from? *Neuroscience & Biobehavioral Reviews, 34*(4), 575–583.

Hickok, G. (2009). Eight problems for the mirror neuron theory of action understanding in monkeys and humans.
*Journal of Cognitive Neuroscience, 21*(7), 1229–1243.

Holmes, P., & Calmels, C. (2008). A neuroscientific review of imagery and observation use in sport. *Journal of
Motor Behavior, 40*(5), 433–445.

Hove, M. J., & Risen, J. L. (2009). It's all in the timing: Interpersonal synchrony increases affiliation.
*Social Cognition, 27*(6), 949–960.

Jaeggi, S. M., Buschkuehl, M., Jonides, J., & Perrig, W. J. (2008). Improving fluid intelligence with training on
working memory. *Proceedings of the National Academy of Sciences, 105*(19), 6829–6833.

Jeannerod, M. (2001). Neural simulation of action: A unifying mechanism for motor cognition. *NeuroImage, 14*(1),
S103–S109.

Johansson, G. (1973). Visual perception of biological motion and a model for its analysis. *Perception &
Psychophysics, 14*(2), 201–211.

Kane, M. J., Conway, A. R. A., Miura, T. K., & Colflesh, G. J. H. (2007). Working memory, attention control, and
the n-back task: A question of construct validity. *Journal of Experimental Psychology: Learning, Memory, and
Cognition, 33*(3), 615–622.

Kilner, J. M., Friston, K. J., & Frith, C. D. (2007). Predictive coding: An account of the mirror neuron system.
*Cognitive Processing, 8*(3), 159–166.

Kirchner, W. K. (1958). Age differences in short-term retention of rapidly changing information. *Journal of
Experimental Psychology, 55*(4), 352–358.

Mann, D. T. Y., Williams, A. M., Ward, P., & Janelle, C. M. (2007). Perceptual-cognitive expertise in sport: A
meta-analysis. *Journal of Sport and Exercise Psychology, 29*(4), 457–478.

Mattar, A. A. G., & Gribble, P. L. (2005). Motor learning by observing. *Neuron, 46*(1), 153–160.

McIntosh, D. N., Reichmann-Decker, A., Winkielman, P., & Wilbarger, J. L. (2006). When the social mirror breaks:
Deficits in automatic, but not voluntary, mimicry of emotional facial expressions in autism. *Developmental
Science, 9*(3), 295–302.

Melby-Lervåg, M., & Hulme, C. (2013). Is working memory training effective? A meta-analytic review.
*Developmental Psychology, 49*(2), 270–291.

Milton, D. E. M. (2012). On the ontological status of autism: The "double empathy problem". *Disability &
Society, 27*(6), 883–887.

Miyake, A., Friedman, N. P., Emerson, M. J., Witzki, A. H., Howerter, A., & Wager, T. D. (2000). The unity and
diversity of executive functions and their contributions to complex "frontal lobe" tasks: A latent variable
analysis. *Cognitive Psychology, 41*(1), 49–100.

Mukamel, R., Ekstrom, A. D., Kaplan, J., Iacoboni, M., & Fried, I. (2010). Single-neuron responses in humans
during execution and observation of actions. *Current Biology, 20*(8), 750–756.

Neal, D. T., & Chartrand, T. L. (2011). Embodied emotion perception: Amplifying and dampening facial feedback
modulates emotion perception accuracy. *Social Psychological and Personality Science, 2*(6), 673–678.

Niedenthal, P. M., Mermillod, M., Maringer, M., & Hess, U. (2010). The Simulation of Smiles (SIMS) model:
Embodied simulation and the meaning of facial expression. *Behavioral and Brain Sciences, 33*(6), 417–433.

Oberauer, K. (2002). Access to information in working memory: Exploring the focus of attention. *Journal of
Experimental Psychology: Learning, Memory, and Cognition, 28*(3), 411–421.

Oberman, L. M., Winkielman, P., & Ramachandran, V. S. (2007). Face to face: Blocking facial mimicry can
selectively impair recognition of emotional expressions. *Social Neuroscience, 2*(3–4), 167–178.

Owen, A. M., McMillan, K. M., Laird, A. R., & Bullmore, E. (2005). N-back working memory paradigm: A meta-analysis
of normative functional neuroimaging studies. *Human Brain Mapping, 25*(1), 46–59.

Parsons, L. M. (1987). Imagined spatial transformations of one's hands and feet. *Cognitive Psychology, 19*(2),
178–241.

Rizzolatti, G., & Craighero, L. (2004). The mirror-neuron system. *Annual Review of Neuroscience, 27*, 169–192.

Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning: Taking memory tests improves long-term
retention. *Psychological Science, 17*(3), 249–255.

Sakai, K., Kitaguchi, K., & Hikosaka, O. (2003). Chunking during human visuomotor sequence learning.
*Experimental Brain Research, 152*(2), 229–242.

Sala, G., & Gobet, F. (2019). Cognitive training does not enhance general cognition. *Trends in Cognitive
Sciences, 23*(1), 9–20.

Salmoni, A. W., Schmidt, R. A., & Walter, C. B. (1984). Knowledge of results and motor learning: A review and
critical reappraisal. *Psychological Bulletin, 95*(3), 355–386.

Shea, J. B., & Morgan, R. L. (1979). Contextual interference effects on the acquisition, retention, and transfer
of a motor skill. *Journal of Experimental Psychology: Human Learning and Memory, 5*(2), 179–187.

Simons, D. J., Boot, W. R., Charness, N., Gathercole, S. E., Chabris, C. F., Hambrick, D. Z., & Stine-Morrow,
E. A. L. (2016). Do "brain-training" programs work? *Psychological Science in the Public Interest, 17*(3),
103–186.

Smyth, M. M., Pearson, N. A., & Pendleton, L. R. (1988). Movement and working memory: Patterns and positions in
space. *Quarterly Journal of Experimental Psychology A, 40*(3), 497–514.

Smyth, M. M., & Pendleton, L. R. (1989). Working memory for movements. *Quarterly Journal of Experimental
Psychology A, 41*(2), 235–250.

Smyth, M. M., & Pendleton, L. R. (1990). Space and movement in working memory. *Quarterly Journal of
Experimental Psychology A, 42*(2), 291–304.

Southgate, V., & Hamilton, A. F. de C. (2008). Unbroken mirrors: Challenging a theory of autism. *Trends in
Cognitive Sciences, 12*(6), 225–229.

Soveri, A., Antfolk, J., Karlsson, L., Salo, B., & Laine, M. (2017). Working memory training revisited: A
multi-level meta-analysis of n-back training studies. *Psychonomic Bulletin & Review, 24*(4), 1077–1096.

Stefan, K., Cohen, L. G., Duque, J., Mazzocchio, R., Celnik, P., Sawaki, L., Ungerleider, L., & Classen, J.
(2005). Formation of a motor memory by action observation. *Journal of Neuroscience, 25*(41), 9339–9346.

Strack, F., Martin, L. L., & Stepper, S. (1988). Inhibiting and facilitating conditions of the human smile: A
nonobtrusive test of the facial feedback hypothesis. *Journal of Personality and Social Psychology, 54*(5),
768–777.

Tessari, A., & Rumiati, R. I. (2004). The strategic control of multiple routes in imitation of actions. *Journal
of Experimental Psychology: Human Perception and Performance, 30*(6), 1107–1116.

Vogt, S., Di Rienzo, F., Collet, C., Collins, A., & Guillot, A. (2013). Multiple roles of motor imagery during
action observation. *Frontiers in Human Neuroscience, 7*, 807.

Wagenmakers, E.-J., Beek, T., Dijkhoff, L., Gronau, Q. F., et al. (2016). Registered Replication Report: Strack,
Martin, & Stepper (1988). *Perspectives on Psychological Science, 11*(6), 917–928.

Walker, M. P., Brakefield, T., Morgan, A., Hobson, J. A., & Stickgold, R. (2002). Practice with sleep makes
perfect: Sleep-dependent motor skill learning. *Neuron, 35*(1), 205–211.

Wang, Y., & Hamilton, A. F. de C. (2012). Social top-down response modulation (STORM): A model of the control of
mimicry in social interaction. *Frontiers in Human Neuroscience, 6*, 153.

Williams, J. H. G., Whiten, A., Suddendorf, T., & Perrett, D. I. (2001). Imitation, mirror neurons and autism.
*Neuroscience & Biobehavioral Reviews, 25*(4), 287–295.

Wolpert, D. M., Doya, K., & Kawato, M. (2003). A unifying computational framework for motor control and social
interaction. *Philosophical Transactions of the Royal Society B, 358*(1431), 593–602.

Wood, A., Rychlowska, M., Korb, S., & Niedenthal, P. (2016). Fashioning the face: Sensorimotor simulation
contributes to facial expression recognition. *Trends in Cognitive Sciences, 20*(3), 227–240.

Wood, J. N. (2007). Visual working memory for observed actions. *Journal of Experimental Psychology: General,
136*(4), 639–652.

Woodin, M. E., & Heil, J. (1996). Skilled motor performance and working memory in rowers: Body patterns and
spatial positions. *Quarterly Journal of Experimental Psychology A, 49*(2), 357–378.

Wulf, G., & Shea, C. H. (2002). Principles derived from the study of simple skills do not generalize to complex
skill learning. *Psychonomic Bulletin & Review, 9*(2), 185–211.
