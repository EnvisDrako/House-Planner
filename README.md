# House Planner 🏠



## Overview

House Planner is an innovative tool that leverages a fine-tuned FLAN-T5 model to generate house plans based on user-defined specifications. This project provides an intuitive graphical user interface (GUI) for users to input their requirements and visualize the generated floor plan. Ideal for architects, designers, and individuals looking to create custom living spaces, House Planner streamlines the design process and offers a creative solution for architectural planning.



## Key Features ✨

**Custom House Plan Generation**: Automatically generates house plans based on user inputs such as the number of bedrooms, bathrooms, and total area.

- **Interactive GUI**: A user-friendly interface built with Tkinter allows for easy input of house specifications.

- **Advanced AI Model**: Powered by a fine-tuned FLAN-T5 model, ensuring high-quality and contextually relevant house plan generation.

- **3D Visualization**: Generates an HTML file for 3D visualization of the house plan, providing an immersive and detailed view of the design.

- **Real-Time Validation**: Includes a validation module to ensure the generated house plan adheres to architectural best practices and user constraints.



## How It Works ⚙️

The application follows a streamlined workflow to generate and display house plans:

1. **User Input**: The user specifies the desired number of bedrooms, bathrooms, and total area through the GUI.

2. **Model Inference**: The input is processed by the fine-tuned FLAN-T5 model, which generates a detailed house plan in a structured format.

3. **Validation**: The generated plan is validated to ensure its architectural integrity and correctness.

4. **Visualization**: A 3D representation of the house plan is created and displayed in an HTML file for interactive viewing.



## Technology Stack 🛠️

- **Python**: The core programming language for the project.

- **Tkinter**: For creating the graphical user interface.

- **PyTorch**: The deep learning framework used for model training and deployment.

- **Transformers**: Provides access to the FLAN-T5 model and related utilities.

- **Jupyter Notebook**: For model training, fine-tuning, and experimentation.



## Installation and Setup 🚀

To get House Planner up and running on your local machine, follow these steps:

1. **Clone the Repository**:

   Bash

   ```
   git clone https://github.com/envisdrako/house-planner.git
   cd house-planner

   ```

2. **Install Dependencies**: It is recommended to use a virtual environment to manage dependencies.

   Bash

   ```
   pip install -r requirements.txt

   ```

3. **Download Pre-trained Models**: Ensure you have the fine-tuned FLAN-T5 model files in the `my-flan-model/` directory.



## Usage 🎯

To start generating house plans, run the `GUI.py` script:

Bash

```
python GUI.py

```

Enter your desired specifications in the GUI and click "Generate" to see the 3D visualization of your custom house plan. For details on the model training process, refer to the `Train_Main.ipynb` notebook.



## Contact 📧

For any questions, feedback, or collaboration inquiries, please feel free to reach out. We are always looking to improve and expand the capabilities of this project!
