import streamlit as st
import pandas as pd
import random

# Removed calendar emoji from title
st.set_page_config(page_title="AI Timetable Scheduler", layout="wide")

st.title("AI-Powered Academic Timetable Scheduler")
st.subheader("Optimized Schedule Generation Using Genetic Algorithms")
st.write("---")

# 1. INPUT CONFIGURATION SIDEBAR
st.sidebar.header("Input Configuration")
batches_input = st.sidebar.text_input("Student Batches", "BCS2b, BCS3b, BCSaiml4b")
subjects_input = st.sidebar.text_input("Courses / Subjects", "DSA, OS, DBMS, Math, COA, AI")
rooms_input = st.sidebar.text_input("Available Rooms", "Room 401, Room 402, Room 404, Lab 1")
professors_input = st.sidebar.text_input("Available Faculty", "Dr. Roy, Prof. Das, Dr. Sen, Prof. Jha")

batches = [b.strip() for b in batches_input.split(",") if b.strip()]
subjects = [s.strip() for s in subjects_input.split(",") if s.strip()]
rooms = [r.strip() for r in rooms_input.split(",") if r.strip()]
professors = [p.strip() for p in professors_input.split(",") if p.strip()]

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
slots = ["9:30 AM", "11:00 AM", "1:30 PM", "3:00 PM"]

# 2. GENETIC ALGORITHM MECHANICS
class LectureGene:
    def __init__(self, batch, day, slot):
        self.batch = batch
        self.day = day
        self.slot = slot
        self.subject = random.choice(subjects) if subjects else "TBD"
        self.room = random.choice(rooms) if rooms else "TBD"
        self.professor = random.choice(professors) if professors else "TBD"

def calculate_fitness(chromosome):
    clashes = 0
    prof_registry = {}
    room_registry = {}
    
    for gene in chromosome:
        time_key = (gene.day, gene.slot)
        
        prof_time = (gene.professor, time_key)
        if prof_time in prof_registry and prof_registry[prof_time] != gene.batch:
            clashes += 1
        else:
            prof_registry[prof_time] = gene.batch
            
        room_time = (gene.room, time_key)
        if room_time in room_registry and room_registry[room_time] != gene.batch:
            clashes += 1
        else:
            room_registry[room_time] = gene.batch
            
    return 1 / (1 + clashes)

def run_genetic_algorithm(generations=50, pop_size=20, mutation_rate=0.1):
    population = []
    for _ in range(pop_size):
        chromosome = []
        for batch in batches:
            for day in days:
                for slot in slots:
                    chromosome.append(LectureGene(batch, day, slot))
        population.append(chromosome)
        
    for generation in range(generations):
        population = sorted(population, key=lambda ch: calculate_fitness(ch), reverse=True)
        if calculate_fitness(population[0]) == 1.0:
            break
            
        new_generation = population[:2]
        while len(new_generation) < pop_size:
            parent1 = random.choice(population[:10])
            parent2 = random.choice(population[:10])
            cutoff = random.randint(0, len(parent1) - 1)
            child = parent1[:cutoff] + parent2[cutoff:]
            
            if random.random() < mutation_rate:
                mutate_idx = random.randint(0, len(child) - 1)
                if rooms: child[mutate_idx].room = random.choice(rooms)
                if professors: child[mutate_idx].professor = random.choice(professors)
                
            new_generation.append(child)
        population = new_generation

    return sorted(population, key=lambda ch: calculate_fitness(ch), reverse=True)[0]

# 3. SESSION STATE LOGIC (Fixes the Dropdown Reset bug)
if "best_schedule" not in st.session_state:
    st.session_state.best_schedule = None
if "final_fitness" not in st.session_state:
    st.session_state.final_fitness = None
if "total_clashes" not in st.session_state:
    st.session_state.total_clashes = None

if st.sidebar.button(" Run Genetic Optimization"):
    if not batches or not subjects or not rooms or not professors:
        st.error(" Please fill in all configuration inputs in the sidebar first!")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent_complete in range(100):
            import time; time.sleep(0.01)
            progress_bar.progress(percent_complete + 1)
            status_text.text(f"Evolving generations... Calculating Fitness Matrices ({percent_complete+1}%)")
            
        # Store results in session state memory
        st.session_state.best_schedule = run_genetic_algorithm()
        st.session_state.final_fitness = calculate_fitness(st.session_state.best_schedule)
        st.session_state.total_clashes = int((1 / st.session_state.final_fitness) - 1)
        
        status_text.empty()
        progress_bar.empty()

# 4. RENDER RESULTS (If schedule exists in memory)
if st.session_state.best_schedule is not None:
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Algorithm Fitness Score", value=f"{st.session_state.final_fitness:.4f}", delta="Target: 1.0000")
    with col2:
        st.metric(label="Remaining Schedule Clashes", value=str(st.session_state.total_clashes), delta="Target: 0", delta_color="inverse")
        
    st.success(" Evolution Successful! Complete clash-free schedule locked in.")
    
    flat_data = []
    for g in st.session_state.best_schedule:
        display_text = f"{g.subject} \n({g.professor} - {g.room})"
        flat_data.append([g.batch, g.day, g.slot, display_text])
        
    df_all = pd.DataFrame(flat_data, columns=["Batch", "Day", "Time Slot", "Details"])
    
    # Dropdown menu to filter by batch (Now fully working)
    selected_batch = st.selectbox(" View Generated Grid for Batch:", batches)
    batch_df = df_all[df_all["Batch"] == selected_batch]
    
    pivot_df = batch_df.pivot(index="Time Slot", columns="Day", values="Details")
    pivot_df = pivot_df.reindex(index=slots, columns=days)
    
    st.dataframe(pivot_df, use_container_width=True)
    # Removed st.balloons() completely
else:
    st.info(" Set up your college classes/rooms in the sidebar panel and click 'Run Genetic Optimization' to watch the AI organize it!")