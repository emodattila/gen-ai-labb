# External imports
import streamlit as st
from openai import OpenAI
from groq import Groq
from llama_index.core import VectorStoreIndex, ServiceContext, Document, SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from tavily import TavilyClient

# Python imports
import hmac
import os
from os import environ
import base64
import json
from typing import Dict, List, Any
from uuid import uuid4
import tempfile
import time
import datetime
import pathlib

# Local imports 
from functions.styling import page_config
from functions.menu import menu
import config as c

#############################################
# APPLICATION INITIALIZATION
#############################################

now = datetime.datetime.now()

def initialize_app():
    """
    Initialize the app state and settings.
    """
    # Set page config must be first Streamlit command 
    page_config()

    def load_css(file_path):
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    css_path = pathlib.Path("assets/styles.css")
    load_css(css_path)
    
    # Set up basic UI elements
    st.logo("images/logo_main.png", icon_image="images/logo_small.png")
    
    # Initialize session state variables
    initialize_session_state()
    
    # Load language settings
    load_language_settings()
    
    # Initialize LlamaIndex settings
    initialize_llama_index()

def initialize_session_state():
    """
    Initialize session state variables with default values.
    """
    # Get pwd_on setting with proper environment handling
    if c.deployment == "streamlit":
        pwd_on = st.secrets.get("pwd_on", "false")
    else:
        pwd_on = environ.get("pwd_on", "false") 

    defaults = {
        # User preferences
        'language': "Svenska",
        'llm_temperature': 0.7,
        'llm_chat_model': "OpenAI GPT-4.1",
        
        # Image generation settings
        'image_model': "dall-e-3",
        'image_size': "1024x1024",
        
        # Document settings
        'session_id': str(uuid4()),
        'document_mode': False,
        'document_processing': False,
        'uploaded_documents': [],
        'document_index': None,
        
        # Conversation state
        "messages": [],
        "thinking": False,
        
        # Image context
        "last_image_prompt": None,
        
        # Use the properly determined pwd_on value
        "pwd_on": pwd_on
    }
    
    # Only set values that don't already exist
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
            
    # Create a user-specific data folder
    os.makedirs("data", exist_ok=True)
    user_data_folder = f'./data/{st.session_state["session_id"]}'
    os.makedirs(user_data_folder, exist_ok=True)
    st.session_state['user_data_folder'] = user_data_folder

def initialize_llama_index():
    """
    Initialize LlamaIndex settings for document processing.
    """
    if c.deployment == "streamlit":
        os.environ["OPENAI_API_KEY"] = st.secrets.openai_key
    else:
        os.environ["OPENAI_API_KEY"] = environ.get("openai_key")
    
    # Initialize LlamaIndex settings
    Settings.llm = LlamaOpenAI(
        model="gpt-4.1", 
        temperature=st.session_state.llm_temperature,
        system_prompt=st.session_state.system_prompt
    )
    
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=100)

def load_language_settings():
    """
    Load language-specific text based on selected language.
    """
    lang = st.session_state['language']
    
    translations = {
        "Svenska": {
            "chat_prompt": f"""Du är en hjälpsam AI-assistent. Svara på användarens frågor.  

Dagens datum är: {now}.  

Du har tillgång till ett antal olika verktyg:  
- Du kan hjälpa användaren att analysera bilder genom att de laddar upp dem. 
- Du kan generera bilder om användaren ber dig 'skapa en bild av...' eller 'generera en bild av...'
- Du kan söka på webben för att hitta aktuell information om användaren ber dig att 'söka efter...' eller om du behöver aktuell information för att besvara en fråga.""",
            "doc_prompt": """Du är en hjälpsam AI-assistent som hjälper användaren med sina frågor gällande den kontext du fått. Kontexten är ett eller flera dokument. 
Basera alla dina svar på kontexten och hitta inte på något. Hjälp användaren svara på frågor, summera och annat. 
Om du inte vet svaret, svarar du att du inte vet svaret.""",
            "chat_clear_chat": "Ny chatt",
            "chat_hello": "Hej! Hur kan jag hjälpa dig?",
            "chat_settings": "Inställningar",
            "chat_choose_llm": "Välj språkmodell",
            "chat_choose_temp": "Temperatur",
            "chat_system_prompt": "Systemprompt",
            "chat_save": "Spara",
            "chat_input_q": "Vad vill du prata om?",
            "processing": "Bearbetar din förfrågan...",
            "response_complete": "Klar!",
            "error_occurred": "Ett fel inträffade",
            "image_wait": "Skapar din bild...",
            "image_generation_error": "Det uppstod ett fel vid generering av bilden.",
            "image_generating": "Skapar bilden...",
            "document_processing": "Bearbetar ditt dokument...",
            "document_error": "Det uppstod ett fel vid bearbetning av dokumentet.",
            "thinking": "Jag tänker... Ett ögonblick...",
            "text_settings": "Textinställningar",
            "image_settings": "Bildinställningar"
        },
        "English": {
            "chat_prompt": f"""You are a helpful AI assistant. Answer the user's questions.  
Today's date is: {now}.  
You have access to a number of different tools: 
You can help the user analyze images they upload.
You can also generate images if the user asks you to 'create an image of...' or 'generate an image of...'.
You can search the web for current information if the user asks you to 'search for...' or if you need up-to-date information to answer a question.""",
            "doc_prompt": """You are a helpful AI assistant that helps the user with their questions regarding the context you have received. The context is one or more documents.  
Base all your answers on the context and do not make anything up. Help the user answer questions, summarize, and other tasks. 
If you don't know the answer, respond that you don't know the answer.""",
            "chat_clear_chat": "New chat",
            "chat_hello": "Hi! How can I help you?",
            "chat_settings": "Settings",
            "chat_choose_llm": "Choose language model",
            "chat_choose_temp": "Temperature",
            "chat_system_prompt": "System prompt",
            "chat_save": "Save",
            "chat_input_q": "What do you want to talk about?",
            "processing": "Processing your request...",
            "response_complete": "Done!",
            "error_occurred": "Error occurred",
            "image_wait": "Creating your image...",
            "image_generation_error": "An error occurred while generating the image.",
            "image_generating": "Creating the image...",
            "document_processing": "Processing your document...",
            "document_error": "An error occurred while processing the document.",
            "thinking": "I'm thinking... One moment...",
            "text_settings": "Text settings",
            "image_settings": "Image settings"
        }
    }
    
    # Set the translations in session state
    st.session_state.translations = translations[lang]
    
    # Initialize system prompt if not already set
    if 'system_prompt' not in st.session_state:
        st.session_state.system_prompt = st.session_state.translations["chat_prompt"]
    

#############################################
# PASSWORD PROTECTION
#############################################

def check_password() -> bool:
    """
    Handle password protection for the app.
    
    Returns:
        bool: True if password is correct or not required, False otherwise
    """
    if st.session_state["pwd_on"] != "true":
        return True
        
    if c.deployment == "streamlit":
        passwd = st.secrets["password"]
    else:
        passwd = environ.get("password")

    def password_entered():
        if hmac.compare_digest(st.session_state["password"], passwd):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("Lösenord", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 Ooops. Fel lösenord.")
    return False

#############################################
# DOCUMENT HANDLING
#############################################

def process_document(doc_file):
    """
    Process an uploaded document file for indexing.
    
    Args:
        doc_file: The document file object from streamlit
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a temporary file to save the document
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{doc_file.name.split('.')[-1]}") as tmp_file:
            # Write the file content
            tmp_file.write(doc_file.getvalue())
            file_path = tmp_file.name
        
        # Add to list of processed documents
        if file_path not in st.session_state.uploaded_documents:
            st.session_state.uploaded_documents.append({
                'path': file_path,
                'name': doc_file.name
            })
            
        return True
    
    except Exception as e:
        st.error(f"{st.session_state.translations['document_error']} {str(e)}")
        return False

def create_document_index(status=None):
    """
    Create a vector index from the uploaded documents.
    
    Args:
        status: Optional Streamlit status object to update
        
    Returns:
        VectorStoreIndex: The created index
    """
    if not st.session_state.uploaded_documents:
        st.session_state.document_processing = False
        return None
    
    try:
        # Create documents from the files
        documents = []
        for doc_info in st.session_state.uploaded_documents:
            file_path = doc_info['path']
            file_name = doc_info['name']
            
            # Use SimpleDirectoryReader for the file
            if os.path.exists(file_path):
                if status:
                    status.update(label=f"Processing {file_name}...")
                
                reader = SimpleDirectoryReader(input_files=[file_path])
                docs = reader.load_data()
                
                if status:
                    status.update(label=f"Completed processing {file_name}")
                
                documents.extend(docs)
        
        if not documents:
            st.session_state.document_processing = False
            return None
            
        # Create index with progress indicator
        if status:
            status.update(label="Delar upp och fixar ditt dokument...")
            
        index = VectorStoreIndex.from_documents(
            documents,
            show_progress=True
        )
        
        # Clean up temporary files after indexing
        for doc_info in st.session_state.uploaded_documents:
            file_path = doc_info['path']
            if os.path.exists(file_path):
                os.unlink(file_path)
                
        # Clear the list but keep document mode on
        st.session_state.uploaded_documents = []
        
        return index
        
    except Exception as e:
        st.error(f"Error processing documents: {str(e)}")
        st.session_state.document_processing = False
        return None

def query_document(query, message_placeholder):
    """
    Query the document index with user question.
    
    Args:
        query: User's query text
        message_placeholder: Streamlit placeholder for streaming responses
        
    Returns:
        str: Full response text
    """
    # Create index if needed
    if st.session_state.document_index is None:
        st.session_state.document_index = create_document_index()
        
    if st.session_state.document_index is None:
        return "I don't have any documents to reference. Please upload a document first."
    
    # Create query engine
    query_engine = st.session_state.document_index.as_query_engine(
        similarity_top_k=10
    )
    
    # Process the query (non-streaming first to avoid the attribute error)
    with st.spinner(st.session_state.translations["thinking"]):
        response = query_engine.query(query)
        return response.response  # Return the string response directly

#############################################
# IMAGE HANDLING
#############################################

def encode_image_for_api(image_file) -> str:
    """
    Encode an image file to base64 for API submission.
    
    Args:
        image_file: The image file object to encode
        
    Returns:
        str: Base64 encoded image string
    """
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def format_multimodal_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a message with text and images for vision models.
    
    Args:
        message: The message to format
        
    Returns:
        Dict: Formatted message ready for API submission
    """
    # Regular text-only message
    if "image_files" not in message or not message["image_files"]:
        return {"role": message["role"], "content": message["content"]}
    
    # Message with images
    content = [{"type": "text", "text": message["content"]}]
    
    # Add image content
    for img_file in message["image_files"]:
        # Encode the image
        base64_image = encode_image_for_api(img_file)
        
        # Add to content array
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })
    
    return {"role": message["role"], "content": content}

def cleanup_image_data_after_processing():
    """
    Clean up image data after processing by preserving display images.
    """
    for i, message in enumerate(st.session_state.messages):
        if "image_files" in message:
            # Keep images for display only
            if "display_images" not in message:
                message["display_images"] = message["image_files"]
            
            # Remove the image_files key entirely - we don't need it for future API calls
            del message["image_files"]
            
            # Update the message in session state
            st.session_state.messages[i] = message

#############################################
# TOOL DEFINITIONS AND EXECUTION
#############################################

def define_tools():
    """
    Define the tools that the LLM can use, including image generation and web search.
    
    Returns:
        list: List of tool definitions in the format expected by the API
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": "Generate an image based on a text description. Call this function when the user wants to create an image or modify a previously generated image.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "A detailed text description of the image to generate"
                        },
                        "is_modification": {
                            "type": "boolean",
                            "description": "Whether this is modifying a previous image"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["1024x1024", "1792x1024", "1024x1792"],
                            "description": "The size of the image to generate"
                        }
                    },
                    "required": ["prompt"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current information. Use this when the user asks for recent or specific information that might not be in your knowledge base, or when they explicitly ask to search the web.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to send to the web search engine"
                        },
                        "include_answer": {
                            "type": "string",
                            "enum": ["true", "false", "basic", "advanced"],
                            "description": "Whether to include an AI-generated answer in the response",
                            "default": "advanced"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    return tools

def execute_image_generation_tool(tool_call, message_placeholder):
    """
    Execute the image generation tool called by the LLM.
    
    Args:
        tool_call: The tool call parameters from the LLM
        message_placeholder: Streamlit placeholder for status updates
        
    Returns:
        tuple: (image_url, prompt) - The generated image URL and the prompt used
    """
    try:
        # Parse the tool call arguments
        arguments = json.loads(tool_call["arguments"])
        prompt = arguments["prompt"]
        is_modification = arguments.get("is_modification", False)
        size = arguments.get("size", st.session_state["image_size"])
        
        # Show generation status
        with st.spinner(st.session_state.translations["image_generating"], show_time=True):
            # Get the OpenAI client
            if c.deployment == "streamlit":
                client = OpenAI(api_key=st.secrets.openai_key)
            else:
                client = OpenAI(api_key=environ.get("openai_key"))
            
            # If this is a modification, add context if helpful
            final_prompt = prompt
            if is_modification and st.session_state.get("last_image_prompt"):
                final_prompt = f"Based on this previous idea: {st.session_state['last_image_prompt']}, now {prompt}"
            
            # Generate the image
            response = client.images.generate(
                model=st.session_state["image_model"],
                prompt=final_prompt,
                size=size,
                style="vivid",
                n=1,
            )
            
            # Save this prompt for future reference
            st.session_state["last_image_prompt"] = final_prompt
            
            # Return the image URL and prompt
            return response.data[0].url, final_prompt
            
    except Exception as e:
        error_msg = f"{st.session_state.translations['image_generation_error']} {str(e)}"
        st.error(error_msg)
        message_placeholder.markdown(error_msg)
        return None, ""

def execute_web_search_tool(tool_call, message_placeholder):
    """
    Execute the web search tool called by the LLM.
    
    Args:
        tool_call: The tool call parameters from the LLM
        message_placeholder: Streamlit placeholder for status updates
        
    Returns:
        str: The search results as a formatted string
    """
    try:
        # Parse the tool call arguments
        arguments = json.loads(tool_call["arguments"])
        query = arguments["query"]
        include_answer = arguments.get("include_answer", "advanced")
        
        # Get the current language from session state
        current_language = st.session_state.get('language', 'English')
        
        # Modify the query to include language instructions for non-English searches
        original_query = query
        if current_language == "Svenska":
            # Add Swedish language instruction to the query
            query = f"{query} (answer in Swedish)"
            search_message = f"_Söker på webben efter: '{original_query}'_"
        else:
            search_message = f"_Searching the web for: '{original_query}'_"
        
        # Show search status
        with st.spinner(search_message, show_time=True):
        #message_placeholder.markdown(search_message)
        
            # Initialize Tavily client
            if c.deployment == "streamlit":
                client = TavilyClient(st.secrets.tavily_key)
            else:
                client = TavilyClient(environ.get("tavily_key"))
            
            # Execute the search
            response = client.search(
                query=query,
                include_answer=include_answer
            )
        
        # Format the response according to the current language
        if current_language == "Svenska":
            result = f"**Sökresultat:** '{original_query}'\n\n"
            
            # Add AI answer if available
            if "answer" in response and response["answer"]:
                result += f"\n{response['answer']}\n\n"
            
            # Add search results
            result += "**Källor:**\n"
            for idx, source in enumerate(response.get("results", [])[:5], 1):  # Limit to top 5 results
                result += f"{idx}. [{source['title']}]({source['url']})\n"
                #result += f"   {source.get('description', 'Ingen beskrivning tillgänglig')}\n\n"
        else:
            result = f"**Search Results:** '{original_query}'\n\n"
            
            # Add AI answer if available
            if "answer" in response and response["answer"]:
                result += f"\n{response['answer']}\n\n"
            
            # Add search results
            result += "**Sources:**\n"
            for idx, source in enumerate(response.get("results", [])[:5], 1):  # Limit to top 5 results
                result += f"{idx}. [{source['title']}]({source['url']})\n"
                #result += f"   {source.get('description', 'No description available')}\n\n"
        
        return result
            
    except Exception as e:
        # Format error messages according to the current language
        if st.session_state.get('language', 'English') == "Svenska":
            error_msg = f"Ett fel uppstod vid sökning på webben: {str(e)}"
            message_placeholder.markdown(error_msg)
            return f"Jag stötte på ett fel när jag försökte söka på webben: {str(e)}. Vänligen försök med en annan sökning eller försök igen senare."
        else:
            error_msg = f"Error executing web search: {str(e)}"
            message_placeholder.markdown(error_msg)
            return f"I encountered an error while trying to search the web: {str(e)}. Please try a different query or try again later."
        

#############################################
# LLM API HANDLING
#############################################

def get_llm_client():
    """
    Get the appropriate LLM client based on model selection.
    
    Returns:
        object: The API client (OpenAI or Groq)
    """
    if "OpenAI" in st.session_state["llm_chat_model"]:
        if c.deployment == "streamlit":
            return OpenAI(api_key=st.secrets.openai_key)
        else:
            return OpenAI(api_key=environ.get("openai_key"))
    else:
        if c.deployment == "streamlit":
            return Groq(api_key=st.secrets.groq_key)
        else:
            return Groq(api_key=environ.get("groq_key"))

def get_model_name() -> str:
    """
    Map selected model name to API model identifier.
    
    Returns:
        str: The API model identifier
    """
    model_map = {
        "OpenAI GPT-4.1": "gpt-4.1",
        "Deep Seek R1 70B": "deepseek-r1-distill-llama-70b", 
        "Gemma2 9B": "gemma2-9b-it",
        "Llama 4 Scout": "meta-llama/llama-4-scout-17b-16e-instruct"
    }
    return model_map[st.session_state["llm_chat_model"]]

def is_vision_capable_model() -> bool:
    """
    Check if the selected model supports image understanding.
    
    Returns:
        bool: True if the model supports vision/images, False otherwise
    """
    return (
        ("OpenAI" in st.session_state["llm_chat_model"] and 
        ("GPT-4.1" in st.session_state["llm_chat_model"])) or
        st.session_state["llm_chat_model"] == "Llama 4 Scout"
    )

def prepare_messages() -> List[Dict[str, Any]]:
    """
    Prepare messages for sending to the LLM API.
    
    Returns:
        List[Dict]: List of message objects ready for API submission
    """
    processed_messages = []
    
    # Add system message first
    processed_messages.append({"role": "system", "content": st.session_state.system_prompt})
    
    # Determine if we're using a vision-capable model
    vision_capable = is_vision_capable_model()
    
    # Process all messages in conversation history
    for message in st.session_state.messages:
        if message["role"] == "user":
            # Check if this message has image files to process
            if vision_capable and "image_files" in message and message["image_files"]:
                # Process this image
                processed_message = format_multimodal_message(message)
                processed_messages.append(processed_message)
            else:
                # Regular text-only message
                processed_messages.append({"role": "user", "content": message["content"]})
        else:
            # Assistant message, pass through as is
            processed_messages.append({"role": "assistant", "content": message["content"]})
    
    return processed_messages

def process_text_only_messages(processed_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert multimodal messages to text-only for non-vision models.
    
    Args:
        processed_messages: The messages containing possible image content
        
    Returns:
        List[Dict]: Text-only messages for use with text-only models
    """
    text_only_messages = []
    
    for m in processed_messages:
        if isinstance(m["content"], list):  # This is a multimodal message
            # Extract just the text parts
            text_parts = [item["text"] for item in m["content"] if item["type"] == "text"]
            text_only_messages.append({
                "role": m["role"],
                "content": " ".join(text_parts) + " [Image description not supported by this model]"
            })
        else:
            text_only_messages.append(m)
    
    return text_only_messages

def process_llm_request(client, processed_messages, message_placeholder, is_document_query=False):
    """
    Process the LLM request with streaming output to the UI.
    
    Args:
        client: The API client (OpenAI or compatible)
        processed_messages: The prepared message objects
        message_placeholder: Streamlit placeholder for streaming the response
        is_document_query: Whether this is a document query (bypass normal processing)
        
    Returns:
        tuple: (response_text, tool_calls)
            - response_text: The text response from the LLM
            - tool_calls: Any tool calls the LLM requested (or None)
    """
    # For document queries, we use the document index instead
    if is_document_query and st.session_state.document_mode:
        # Extract the user's question from the last message
        user_question = ""
        for msg in reversed(processed_messages):
            if msg["role"] == "user":
                user_question = msg["content"]
                break
        
        if not user_question:
            return "I couldn't understand your question. Please try again.", None
        
        # Use non-streaming for document queries to avoid the error
        response_text = query_document(user_question, message_placeholder)
        
        # Display the response with typing effect
        full_response = ""
        for char in response_text:
            full_response += char
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.005)  # Small delay to create typing effect
            
        return response_text, None
    
    # Normal LLM processing (rest of the function stays the same)
    full_response = ""
    tool_calls = None
    model_name = get_model_name()
    temperature = st.session_state["llm_temperature"]
    
    # Only OpenAI models currently support tools
    if "OpenAI" in st.session_state["llm_chat_model"]:
        # Define available tools for the LLM
        tools = define_tools()
        
        # Create the stream with tool calling enabled
        stream = client.chat.completions.create(
            model=model_name,
            temperature=temperature,
            messages=processed_messages,
            tools=tools,
            tool_choice="auto",  # Let the model decide when to use tools
            stream=True,
        )
        
        # Process the streaming response
        collected_tool_calls = {}
        
        for chunk in stream:
            # Handle text responses
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                message_placeholder.markdown(full_response + "▌")
            
            # Handle tool calls
            delta = chunk.choices[0].delta
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    # Get or create the tool call entry
                    tool_call_id = tool_call.index
                    
                    if tool_call_id not in collected_tool_calls:
                        collected_tool_calls[tool_call_id] = {
                            "name": "",
                            "arguments": ""
                        }
                    
                    # Update the tool call data
                    if hasattr(tool_call.function, 'name') and tool_call.function.name:
                        collected_tool_calls[tool_call_id]["name"] = tool_call.function.name
                    
                    if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
                        collected_tool_calls[tool_call_id]["arguments"] += tool_call.function.arguments
        
        # Convert collected tool calls to a more usable format
        if collected_tool_calls:
            tool_calls = list(collected_tool_calls.values())
    else:
        # For non-OpenAI models, just handle text responses
        if st.session_state["llm_chat_model"] == "Llama 4 Scout":
            stream = client.chat.completions.create(
                messages=processed_messages,
                model=model_name,
                temperature=temperature,
                max_tokens=1024,
                top_p=1,
                stop=None,
                stream=True,
            )
        else:
            # For non-vision models, extract just the text
            text_only_messages = process_text_only_messages(processed_messages)
            
            stream = client.chat.completions.create(
                messages=text_only_messages,
                model=model_name,
                temperature=temperature,
                max_tokens=1024,
                top_p=1,
                stop=None,
                stream=True,
            )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += str(chunk.choices[0].delta.content)
                message_placeholder.markdown(full_response + "▌")
    
    return full_response, tool_calls


def handle_error(error_message: str, message_placeholder):
    """
    Handle API errors with specific user-friendly messages.
    
    Args:
        error_message: The error message from the API
        message_placeholder: Streamlit placeholder for streaming the response
    """
    error_patterns = {
        "content_filter": "The image couldn't be processed due to content restrictions.",
        "file_too_large": "The image is too large. Please try with a smaller image.",
        "rate_limit": "Rate limit exceeded. Please try again in a moment.",
        "invalid_api_key": "API authentication error. Please check API key configuration.",
        "context_length": "The conversation is too long. Please clear the chat and start a new one.",
        "token limit": "The conversation is too long. Please clear the chat and start a new one."
    }
    
    for pattern, message in error_patterns.items():
        if pattern in error_message.lower():
            st.error(message)
            return
            
    # Default error message
    st.error(f"Error: {error_message}")

def generate_response(message_placeholder):
    """
    Generate a response from the selected LLM with appropriate UI feedback.
    
    Args:
        message_placeholder: Streamlit placeholder for streaming the response
    """
    try:
        # Get client and prepare messages
        client = get_llm_client()
        processed_messages = prepare_messages()
        
        # Check if we're in document mode
        is_document_query = st.session_state.document_mode
        
        # Process the request
        full_response, tool_calls = process_llm_request(
            client, 
            processed_messages, 
            message_placeholder,
            is_document_query
        )
        
        # Handle any tool calls the LLM requested
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call["name"] == "generate_image":
                    # Clear existing content from placeholder
                    message_placeholder.empty()
                    
                    # Execute the image generation
                    image_url, final_prompt = execute_image_generation_tool(tool_call, message_placeholder)
                    
                    if image_url:
                        # Display the image
                        st.image(image_url, caption=final_prompt)
                        
                        # Add to conversation history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": image_url
                        })
                        
                        # If there was also a text response, add it too
                        if full_response.strip():
                            st.markdown(full_response)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": full_response
                            })
                        
                        return  # Exit after handling the image generation
                
                elif tool_call["name"] == "web_search":
                    # Execute the web search
                    search_result = execute_web_search_tool(tool_call, message_placeholder)
                    
                    # Combine search results with the LLM's response
                    combined_response = ""
                    if full_response.strip():
                        combined_response = full_response + "\n\n" + search_result
                    else:
                        combined_response = search_result
                    
                    # Display the combined response
                    message_placeholder.markdown(combined_response)
                    
                    # Add to conversation history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": combined_response
                    })
                    
                    return  # Exit after handling the web search
        
        # If no tool calls or just regular text response
        message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
                
    except Exception as e:
        # Handle errors
        error_message = str(e)
        handle_error(error_message, message_placeholder)
        full_response = "I'm unable to process the request at this time. Is there anything else I can help with?"
        message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

#############################################
# UI COMPONENTS
#############################################

def render_sidebar():
    """
    Render the sidebar components including the menu and model indicator.
    """
    menu()
    
    #st.sidebar.success("Språkmodell: " + st.session_state["llm_chat_model"])
    
    # Show document mode indicator if active
    if st.session_state.document_mode:
        st.sidebar.info("Dokumentläge: Aktivt")
        
    # Show document processing indicator if active
    if st.session_state.get("document_processing", False):
        st.sidebar.warning("Bearbetar dokument...")

def render_message_history():
    """
    Display the message history in the chat interface.
    Filters out system-generated messages.
    """
    for message in st.session_state.messages:
        # Skip system-generated messages
        if message.get("is_system_message", False):
            continue
            
        with st.chat_message(message["role"]):
            # For URLs (generated images)
            if message["role"] == "assistant" and isinstance(message["content"], str) and (
                message["content"].startswith("http") or
                message["content"].startswith("data:image")
            ):
                # Display generated image
                st.image(message["content"])
            else:
                # Display the message content
                st.markdown(message["content"])
            
            # If the message contains display images, show them
            if "display_images" in message and message["display_images"]:
                for file in message["display_images"]:
                    st.image(file)
            # If the message still has image_files (not yet processed), show them
            elif "image_files" in message and message["image_files"]:
                for file in message["image_files"]:
                    st.image(file)

def reset_chat():
    """
    Reset the chat to its initial state.
    """
    st.session_state.messages = [
        {"role": "assistant", "content": st.session_state.translations["chat_hello"]}
    ]
    
    # Reset image context
    if "last_image_prompt" in st.session_state:
        del st.session_state["last_image_prompt"]
    
    # Reset document mode
    st.session_state.document_mode = False
    st.session_state.document_index = None
    st.session_state.uploaded_documents = []
    
    # Reset system prompt to default
    st.session_state.system_prompt = st.session_state.translations["chat_prompt"]

def render_chat_controls():
    """
    Render chat controls including model selection, clear button and settings expander.
    """
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        # Move model selection here
        llm_model = st.selectbox(
            "Model",  # Shorter label to fit in column
            ["Gemma2 9B", "Deep Seek R1 70B", "Llama 4 Scout", "OpenAI GPT-4.1"],
            index=["Gemma2 9B", "Deep Seek R1 70B", "Llama 4 Scout", "OpenAI GPT-4.1"].index(st.session_state["llm_chat_model"]),
            label_visibility="collapsed"  # Hide label to save space
        )
        # Update session state
        st.session_state["llm_chat_model"] = llm_model
    
    with col2:
        if st.button(st.session_state.translations["chat_clear_chat"], type="secondary", icon=":material/new_window:", use_container_width=True):
            # Clear all conversation state
            reset_chat()
            st.rerun()

    with col3:
        with st.expander(st.session_state.translations["chat_settings"], icon=":material/tune:"):
            render_settings()

def render_settings():
    """
    Render settings UI components including temperature, system prompt,
    and image generation settings.
    """
    # Create tabs for different settings
    text_tab, image_tab = st.tabs([st.session_state.translations["text_settings"], st.session_state.translations["image_settings"]])
    
    with text_tab:
        # Model selection has been moved out, only keep temperature here
        llm_temp = st.slider(
            st.session_state.translations["chat_choose_temp"],
            min_value=0.0,
            max_value=2.0,
            step=0.1,
            value=st.session_state["llm_temperature"],
        )

        # Update the session_state
        st.session_state["llm_temperature"] = llm_temp
        
        st.markdown("###### ")

        # System prompt form
        with st.form("system_prompt_form", border=False):
            prompt_input = st.text_area(
                st.session_state.translations["chat_system_prompt"], 
                st.session_state.system_prompt, 
                height=200
            )
            st.session_state.system_prompt = prompt_input
            st.form_submit_button(st.session_state.translations["chat_save"])
    
    with image_tab:
        # Image model selection
        image_model = st.selectbox(
            "Image Generation Model",
            ["dall-e-2", "dall-e-3"],
            index=["dall-e-2", "dall-e-3"].index(st.session_state["image_model"]),
        )
        
        # Update the session_state
        st.session_state["image_model"] = image_model
        
        # Warning about OpenAI model requirements for tools
        if not "OpenAI" in st.session_state["llm_chat_model"]:
            st.warning("Note: Image generation through tool calls requires an OpenAI model. Non-OpenAI models will provide a text response instead.")


def handle_chat_input():
    """
    Process the chat input from the user, preserving their question when uploading documents.
    """
    # Don't allow chat input during document processing
    if st.session_state.get("document_processing", False):
        st.chat_input("Processing document...", disabled=True)
        return
    
    prompt_input = st.chat_input(
        st.session_state.translations["chat_input_q"], 
        accept_file=True, 
        file_type=["jpg", "png", "pdf", "docx", "doc", "xls", "xlsx", "csv", "txt"]
    )
    
    if prompt_input:
        # Handle both text and file (if present)
        text_content = prompt_input.text if hasattr(prompt_input, "text") else prompt_input
        files = prompt_input.get("files", []) if hasattr(prompt_input, "get") else []
        
        # Separate image files from document files
        image_files = []
        document_files = []
        
        for file in files:
            file_ext = file.name.split('.')[-1].lower()
            if file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                image_files.append(file)
            else:
                document_files.append(file)
        
        # Handle document files (with user's question)
        if document_files:
            # Process documents first, preserving the user's original question
            document_processed = False
            
            # Process the documents
            for doc_file in document_files:
                if process_document(doc_file):
                    document_processed = True
            
            if document_processed:
                # Add a message showing document was uploaded (but don't show in UI)
                doc_names = [doc.name for doc in document_files]
                
                # Store the user's actual question for later use
                original_question = text_content
                st.session_state.original_user_question = original_question
                
                # Add the document upload message (but don't replace the user's question)
                st.session_state.messages.append({
                    "role": "user", 
                    "content": f"I've uploaded the following document(s): {', '.join(doc_names)}.",
                    "is_system_message": True  # Mark as system message so we know it wasn't typed by user
                })
                
                # Set document mode
                st.session_state.document_mode = True
                st.session_state.system_prompt = st.session_state.translations["doc_prompt"]
                
                # Start document processing
                st.session_state.document_processing = True
                
                # Rerun to start processing
                st.rerun()
            
        # If no document was processed or only images, handle as normal image/text
        if not document_files or not document_processed:
            # Create a message object based on what was provided
            if text_content and image_files:
                # Both text and image
                message = {
                    "role": "user", 
                    "content": text_content,
                    "image_files": image_files
                }
            elif image_files:
                # Only image
                message = {
                    "role": "user", 
                    "content": "I've uploaded an image.",
                    "image_files": image_files
                }
            else:
                # Only text
                message = {
                    "role": "user", 
                    "content": text_content
                }
            
            # Add message to conversation history
            st.session_state.messages.append(message)
            
            # Set flag for processing response
            st.session_state["thinking"] = True
            
            # Rerun to display the user message immediately
            st.rerun()

def process_assistant_response():
    """
    Process and generate the assistant's response.
    All image generation is now handled via LLM tool calls.
    """
    # Handle LLM response (which may include image generation via tool calls)
    if st.session_state.get("thinking", False):
        # Clear the thinking flag
        st.session_state["thinking"] = False
        
        # Process response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            generate_response(message_placeholder)
        
        # Clean up image data after processing
        cleanup_image_data_after_processing()

#############################################
# MAIN APPLICATION
#############################################

def main():
    """
    Main application entry point with improved document handling.
    """
    # Initialize app state and UI
    initialize_app()
    
    # Check password if enabled
    if not check_password():
        st.stop()
    
    # Render sidebar
    render_sidebar()
    
    # Render chat UI components
    render_chat_controls()
    
    # Process documents if needed (before rendering chat history)
    if st.session_state.get("document_processing", False) and st.session_state.document_index is None:
        # Create the document index with status display
        with st.status(st.session_state.translations["document_processing"], expanded=True) as status:
            st.session_state.document_index = create_document_index(status)
            
            # Add processing complete message
            if st.session_state.document_index is not None:
                status.update(label=st.session_state.translations["response_complete"], state="complete")
                
                # Check if we have the original question to use
                if hasattr(st.session_state, 'original_user_question') and st.session_state.original_user_question:
                    # Add the user's original question to the chat history
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": st.session_state.original_user_question
                    })
                    
                    # Set thinking flag to trigger answering this question
                    st.session_state["thinking"] = True
                    
                    # Clear the stored question
                    original_question = st.session_state.original_user_question
                    st.session_state.original_user_question = None
                    
                    # No longer processing
                    st.session_state.document_processing = False
                
                # If no original question, just stop processing
                else:
                    st.session_state.document_processing = False
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "You can now ask me questions about the content."
                    })
    
    # Render chat history (filter out system messages)
    render_message_history()
    
    # Handle user input - only enable when not processing documents
    if not st.session_state.get("document_processing", False):
        handle_chat_input()
    else:
        # Show disabled chat input with processing message
        st.chat_input("Processing document...", disabled=True)
    
    # Process assistant response if needed
    process_assistant_response()

# Run the app
if __name__ == "__main__":
    main()