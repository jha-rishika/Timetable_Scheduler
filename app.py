import streamlit as st
import pandas as pd
import random
import time

# =========================================================================
# 1. UI CONFIGURATION & CUSTOM STYLING
# =========================================================================
st.set_page_config(page_title="AI Timetable Scheduler", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.4rem; font-weight: 700; color: #FAFAFA; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1.1rem; color: #A3A3A3; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.title("Campus AI Timetable Scheduler")
st.caption("Department-Aware Automated Course Scheduling Engine powered by Constrained Genetic Optimization")
st.write("") 

# =========================================================================
# 2. SIDEBAR - CONFIGURATION PANEL & DEPARTMENT INPUT DATA
# =========================================================================
st.sidebar.header("Configuration Panel")

st.sidebar.subheader("Academic Inputs (Department-Siloed)")
st.sidebar.info("Format Tip: Prefix subjects and professors with their Department code followed by a colon (e.g., CSE: Subject or BasicSci: Name).")

default_batches = "BCS-2A, BCS-2B, BME-3A"
default_subjects = "CSE: Data Structures, CSE: Java Lab, ECE: Computer Architecture, BasicSci: Discrete Math, CSE: Operating Systems"
default_rooms = "Room 301, Room 302, Computing Lab 1, Electronics Lab"
default_professors = "BasicSci: Dr. P. Roy, CSE: Prof. S. Das, ECE: Dr. A. Sen, CSE: Prof. M. Mitra"

batches_input = st.sidebar.text_area("Batches / Sections (Comma separated)", default_batches)
subjects_input = st.sidebar.text_area("Subjects / Courses (With Dept Prefix)", default_subjects)
rooms_input = st.sidebar.text_area("Available Classrooms (Comma separated)", default_rooms)
professors_input = st.sidebar.text_area("Faculty Members (With Dept Prefix)", default_professors)

# Clean structural parsing
batches = [b.strip() for b in batches_input.split(",") if b.strip()]
rooms = [r.strip() for r in rooms_input.split(",") if r.strip()]

subjects_list = []
professors_list = []
dept_subjects = {}  
dept_profs = {}     

for s in subjects_input.split(","):
    if ":" in s:
        dept, sub_name = s.split(":", 1)
        dept, sub_name = dept.strip(), sub_name.strip()
        if sub_name not in subjects_list:
            subjects_list.append(sub_name)
        dept_subjects.setdefault(dept, []).append(sub_name)

for p in professors_input.split(","):
    if ":" in p:
        dept, prof_name = p.split(":", 1)
        dept, prof_name = dept.strip(), prof_name.strip()
        if prof_name not in professors_list:
            professors_list.append(prof_name)
        dept_profs.setdefault(dept, []).append(prof_name)

st.sidebar.markdown("---")

st.sidebar.subheader("GA Hyperparameters")
user_generations = st.sidebar.slider("Max Generations", min_value=10, max_value=500, value=200, step=10)
user_pop_size = st.sidebar.slider("Population Size Pool", min_value=10, max_value=100, value=50, step=5)
user_mutation_rate = st.sidebar.slider("Mutation Probability", min_value=0.01, max_value=0.50, value=0.20, step=0.01)

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
slots = ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM"]
total_slots_per_batch = len(days) * len(slots) 

# =========================================================================
# DOMAIN CONSTRAINTS & EXPERTISE GENERATOR
# =========================================================================
faculty_specialization = {}
subject_to_prof = {}
all_departments = set(dept_subjects.keys()).union(set(dept_profs.keys()))

guardrail_failed = False
guardrail_error_msg = ""

for dept in all_departments:
    dept_subs = dept_subjects.get(dept, [])
    dept_teachers = dept_profs.get(dept, [])
    
    if len(dept_subs) > 0 and len(dept_teachers) == 0:
        guardrail_failed = True
        guardrail_error_msg = f"Department Resource Deficiency: Department '{dept}' has courses but 0 faculty members."
        break
    elif len(dept_teachers) > 0 and len(dept_subs) == 0:
        guardrail_failed = True
        guardrail_error_msg = f"Department Resource Deficiency: Department '{dept}' has faculty but 0 courses."
        break

    if dept_teachers and dept_subs:
        random.seed(42)
        for idx, sub in enumerate(dept_subs):
            prof = dept_teachers[idx % len(dept_teachers)]
            faculty_specialization.setdefault(prof, []).append(sub)
            subject_to_prof[sub] = prof

for prof, subs in list(faculty_specialization.items()):
    if len(subs) > 2:
        faculty_specialization[prof] = subs[:2]
        dept = [d for d, s in dept_subjects.items() if subs[2] in s][0]
        alt_profs = [p for p in dept_profs[dept] if p != prof]
        if alt_profs:
            faculty_specialization[alt_profs[0]].append(subs[2])
            subject_to_prof[subs[2]] = alt_profs[0]

subject_quotas = {}
if subjects_list:
    base_quota = total_slots_per_batch // len(subjects_list)
    remainder = total_slots_per_batch % len(subjects_list)
    for idx, sub in enumerate(subjects_list):
        subject_quotas[sub] = base_quota + (1 if idx < remainder else 0)

# =========================================================================
# 3. GENETIC ALGORITHM MECHANICS WITH HYBRID OVERFLOW ALIGNMENT
# =========================================================================
class LectureGene:
    def __init__(self, batch, day, slot, subject):
        self.batch = batch
        self.day = day
        self.slot = slot
        self.subject = subject
        self.room = random.choice(rooms) if rooms else "TBD"
        self.professor = subject_to_prof.get(subject, "TBD")

class TimetableChromosome:
    def __init__(self):
        self.genes = []
        for batch in batches:
            shuffled_slots = []
            for sub, count in subject_quotas.items():
                shuffled_slots.extend([sub] * count)
            random.shuffle(shuffled_slots)
            
            idx = 0
            for day in days:
                for slot in slots:
                    self.genes.append(LectureGene(batch, day, slot, shuffled_slots[idx]))
                    idx += 1
        self.fitness = 0.0

    def calculate_fitness(self):
        clashes = 0
        room_occupancy = {}
        prof_occupancy = {}
        
        for g in self.genes:
            time_key = f"{g.day}|{g.slot}"
            
            # --- CONSTRAINT 1: Room Resource Collision ---
            room_key = f"{time_key}|{g.room}"
            if room_key in room_occupancy:
                clashes += 1
            else:
                room_occupancy[room_key] = g.batch
                
            # --- CONSTRAINT 2: Professor Overlap ---
            prof_key = f"{time_key}|{g.professor}"
            if prof_key in prof_occupancy:
                clashes += 1
            else:
                prof_occupancy[prof_key] = g.batch
                
            # --- CONSTRAINT 3: Subject-to-Room Type Matching (With Safe Overflow Failover) ---
            is_lab_subject = "lab" in g.subject.lower() or "programming" in g.subject.lower()
            is_lab_room = "lab" in g.room.lower()
            
            if is_lab_subject and not is_lab_room:
                clashes += 1 # Hard penalty: Labs strictly require specialized equipment rooms
            elif not is_lab_subject and is_lab_room:
                # Soft overflow allocation: Theory courses can occupy labs if no classrooms are free,
                # but it incurs a micro-penalty to prioritize open lecture halls first.
                clashes += 0.1

        self.fitness = 1.0 / (1.0 + clashes)
        return self.fitness

def crossover(parent1, parent2):
    child = TimetableChromosome()
    for i in range(len(child.genes)):
        if random.random() < 0.5:
            child.genes[i].room = parent1.genes[i].room
        else:
            child.genes[i].room = parent2.genes[i].room
    return child

def mutate(chromosome, mutation_rate):
    for gene in chromosome.genes:
        if random.random() < mutation_rate:
            gene.room = random.choice(rooms) if rooms else "TBD"

# =========================================================================
# 4. RUN OPTIMIZATION CONTROL
# =========================================================================
col_btn, _ = st.columns([1, 2])
with col_btn:
    force_run = st.button("Force Re-Optimize & Evolve", use_container_width=True)

if not (batches and subjects_list and rooms and professors_list):
    st.error("System Incomplete: Please ensure all academic fields have entries in the configuration panel.")

elif guardrail_failed:
    st.error(guardrail_error_msg)
else:
    with st.spinner("AI is sorting department boundaries and evolving optimal schedules..."):
        start_time = time.time()
        population = [TimetableChromosome() for _ in range(user_pop_size)]
        
        for generation in range(user_generations):
            for chromosome in population:
                chromosome.calculate_fitness()
            
            population.sort(key=lambda x: x.fitness, reverse=True)
            if population[0].fitness >= 0.99:
                break
                
            mating_pool = population[:int(user_pop_size/2)]
            next_gen = []
            while len(next_gen) < user_pop_size:
                p1 = random.choice(mating_pool)
                p2 = random.choice(mating_pool)
                child = crossover(p1, p2)
                mutate(child, user_mutation_rate)
                next_gen.append(child)
            population = next_gen

        best_schedule = population[0]
        best_schedule.calculate_fitness()
        execution_time = time.time() - start_time

    final_clashes = int((1.0 / best_schedule.fitness) - 1) if best_schedule.fitness > 0 else 0

    if best_schedule.fitness >= 0.95:
        st.success(f"Perfect Multi-Department Optimization Achieved! Zero Clashes. (Fitness: {best_schedule.fitness:.4f})")
    else:
        st.warning(f"Partial Convergence Reached (Fitness: {best_schedule.fitness:.4f}). {final_clashes} constraints mismatched. Try adding more classrooms to expand search space layout options.")
    
    # Render Output Matrix Layout
    data_list = []
    for g in best_schedule.genes:
        data_list.append({
            "Batch": g.batch,
            "Day": g.day,
            "Time Slot": g.slot,
            "Subject": g.subject,
            "Room": g.room,
            "Faculty": g.professor,
            "DisplayCell": f"{g.subject} \n({g.room} - {g.professor})"
        })
    df_all = pd.DataFrame(data_list)

    st.markdown("### Generated Academic Schedules")
    for batch_name in batches:
        df_batch = df_all[df_all["Batch"] == batch_name]
        pivot_df = df_batch.pivot(index="Time Slot", columns="Day", values="DisplayCell")
        pivot_df = pivot_df.reindex(index=slots, columns=days).fillna("---")
        
        st.subheader(f"Section Matrix View: {batch_name}")
        st.dataframe(pivot_df, use_container_width=True)

    # --- DATA SHARING (DOWNLOAD CSV) ---
    st.write("") 
    st.download_button(
        label="Download Full Schedule Dataset (CSV)",
        data=df_all[["Batch", "Day", "Time Slot", "Subject", "Room", "Faculty"]].to_csv(index=False),
        file_name="department_timetable.csv",
        mime="text/csv",
        use_container_width=True
    )

    # --- ADVANCED VIEW MORE SECTION ---
    st.write("")
    with st.expander("View Advanced Evolution Analytics & Department Mapping"):
        st.markdown("#### Execution Summary Logs")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Calculation Runtime", value=f"{execution_time:.3f} seconds")
        with col2:
            st.metric(label="Active Search Space Depth", value=f"Gen {generation + 1}")
        with col3:
            st.metric(label="Rule Violations & Room Clashes", value=str(final_clashes))
            
        st.markdown("#### Department Silo Faculty Registry")
        st.write("Below is the internal mapping showing how the AI grouped professors exclusively with matching department courses:")
        st.json(faculty_specialization)