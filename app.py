import streamlit as st
import pandas as pd
import random
import time

# =========================================================================
# 1. UI CONFIGURATION & STYLING
# =========================================================================
st.set_page_config(page_title="AI Timetable Scheduler", page_icon="🧬", layout="wide")

st.title("🧬 Campus AI Timetable Scheduler")
st.caption("Automated Course Scheduling Engine powered by Genetic Optimization")
st.write("") 

# =========================================================================
# 2. SIDEBAR - CONTROL PANEL & INPUT DATA
# =========================================================================
st.sidebar.header("⚙️ Configuration Panel")

st.sidebar.subheader("🏫 Academic Inputs")
default_batches = "BCS-2A, BCS-2B, BME-3A"
default_subjects = "Data Structures, Computer Architecture, Discrete Math, Operating Systems, Java Programming"
default_rooms = "Room 301, Room 302, Lab 1"
default_professors = "Dr. P. Roy, Prof. S. Das, Dr. A. Sen, Prof. M. Mitra"

batches_input = st.sidebar.text_area("Batches / Sections (Comma separated)", default_batches)
subjects_input = st.sidebar.text_area("Subjects / Courses (Comma separated)", default_subjects)
rooms_input = st.sidebar.text_area("Available Classrooms (Comma separated)", default_rooms)
professors_input = st.sidebar.text_area("Faculty Members (Comma separated)", default_professors)

# Parsing text inputs into clean lists
batches = [b.strip() for b in batches_input.split(",") if b.strip()]
subjects = [s.strip() for s in subjects_input.split(",") if s.strip()]
rooms = [r.strip() for r in rooms_input.split(",") if r.strip()]
professors = [p.strip() for p in professors_input.split(",") if p.strip()]

st.sidebar.markdown("---")

# Moving sliders to the bottom of the sidebar now that they trigger immediate auto-updates
st.sidebar.subheader("🧬 GA Hyperparameters")
user_generations = st.sidebar.slider("Max Generations", min_value=10, max_value=200, value=50, step=10)
user_pop_size = st.sidebar.slider("Population Size Pool", min_value=10, max_value=100, value=20, step=5)
user_mutation_rate = st.sidebar.slider("Mutation Probability", min_value=0.01, max_value=0.50, value=0.10, step=0.01)

# Standard structured institutional timeline parameters
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
slots = ["09:30 AM", "11:00 AM", "01:30 PM", "03:00 PM"]

# =========================================================================
# 3. GENETIC ALGORITHM MECHANICS
# =========================================================================
class LectureGene:
    def __init__(self, batch, day, slot):
        self.batch = batch
        self.day = day
        self.slot = slot
        self.subject = random.choice(subjects) if subjects else "TBD"
        self.room = random.choice(rooms) if rooms else "TBD"
        self.professor = random.choice(professors) if professors else "TBD"

class TimetableChromosome:
    def __init__(self):
        self.genes = []
        for batch in batches:
            for day in days:
                for slot in slots:
                    self.genes.append(LectureGene(batch, day, slot))
        self.fitness = 0.0

    def calculate_fitness(self):
        clashes = 0
        for i in range(len(self.genes)):
            for j in range(i + 1, len(self.genes)):
                g1 = self.genes[i]
                g2 = self.genes[j]
                
                if g1.day == g2.day and g1.slot == g2.slot:
                    if g1.room == g2.room:
                        clashes += 1
                    if g1.professor == g2.professor:
                        clashes += 1
                        
        self.fitness = 1.0 / (1.0 + clashes)
        return self.fitness

def crossover(parent1, parent2):
    child = TimetableChromosome()
    midpoint = random.randint(0, len(parent1.genes) - 1)
    child.genes = parent1.genes[:midpoint] + parent2.genes[midpoint:]
    return child

def mutate(chromosome, mutation_rate):
    for gene in chromosome.genes:
        if random.random() < mutation_rate:
            gene.subject = random.choice(subjects) if subjects else "TBD"
            gene.room = random.choice(rooms) if rooms else "TBD"
            gene.professor = random.choice(professors) if professors else "TBD"

# =========================================================================
# 4. RUN OPTIMIZATION LOGIC (AUTOMATED & MAIN SCREEN ACTION BUTTON)
# =========================================================================

# Clear main screen action anchor point so users instantly know what to click
col_btn, _ = st.columns([1, 2])
with col_btn:
    force_run = st.button("🔄 Force Re-Optimize & Evolve", use_container_width=True)

if not (batches and subjects and rooms and professors):
    st.error("⚠️ Please ensure all academic input fields have at least one entry in the sidebar.")
else:
    # Executes automatically on change OR when the big center button is tapped
    with st.spinner("🧬 AI is dynamically evolving clash-free schedules..."):
        start_time = time.time()
        population = [TimetableChromosome() for _ in range(user_pop_size)]
        
        for generation in range(user_generations):
            for chromosome in population:
                chromosome.calculate_fitness()
            
            population.sort(key=lambda x: x.fitness, reverse=True)
            if population[0].fitness == 1.0:
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

    # Success feedback banner
    st.success(f"✨ Live Dynamic Optimization Active! (Current Fitness Score: {best_schedule.fitness:.4f})")
    
    # Process dataset formatting
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

    # Render out the distinct batch timetable structures
    st.markdown("### 📅 Generated Academic Schedules")
    for batch_name in batches:
        df_batch = df_all[df_all["Batch"] == batch_name]
        pivot_df = df_batch.pivot(index="Time Slot", columns="Day", values="DisplayCell")
        pivot_df = pivot_df.reindex(index=slots, columns=days).fillna("---")
        
        st.subheader(f"📋 Section Matrix View: {batch_name}")
        st.dataframe(pivot_df, use_container_width=True)

    # --- DATA SHARING (DOWNLOAD CSV) ---
    st.write("") 
    st.download_button(
        label="📥 Download Full Schedule Dataset (CSV)",
        data=df_all[["Batch", "Day", "Time Slot", "Subject", "Room", "Faculty"]].to_csv(index=False),
        file_name="ai_generated_timetable.csv",
        mime="text/csv",
        use_container_width=True
    )

    # --- ADVANCED VIEW MORE SECTION (EXPANDER) ---
    st.write("")
    with st.expander("🔍 View Advanced Evolution Analytics"):
        st.markdown("#### 📊 Execution Summary Logs")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Calculation Runtime", value=f"{execution_time:.3f} seconds")
        with col2:
            st.metric(label="Active Search Space Depth", value=f"Gen {generation + 1}")
        with col3:
            st.metric(label="Unresolved Structural Clashes", value=str(final_clashes))
        
        st.info("💡 Concept Note: The Core Fitness optimization score utilizes the objective penalty formulation f(x) = 1 / (1 + Clashes). Adjusting the slider settings in the sidebar changes the processing constraints dynamically.")