const BACKEND_BASE = "http://127.0.0.1:8000";
const REFLECTION_SECONDS = 60;

const pdfFile = document.getElementById("pdfFile");
const instruction = document.getElementById("instruction");
const processBtn = document.getElementById("processBtn");
const resetBtn = document.getElementById("resetBtn");

const uploadStatus = document.getElementById("uploadStatus");
const summaryBox = document.getElementById("summaryBox");
const currentQuestion = document.getElementById("currentQuestion");
const questionCounter = document.getElementById("questionCounter");
const questionTopic = document.getElementById("questionTopic");
const questionStep = document.getElementById("questionStep");

const transcriptBox = document.getElementById("transcriptBox");
const statusBadge = document.getElementById("statusBadge");
const scoreBox = document.getElementById("scoreBox");
const feedbackBox = document.getElementById("feedbackBox");

const prevQuestionBtn = document.getElementById("prevQuestionBtn");
const nextQuestionBtn = document.getElementById("nextQuestionBtn");
const startRecordBtn = document.getElementById("startRecordBtn");
const stopRecordBtn = document.getElementById("stopRecordBtn");

const inlineAgentStep = document.getElementById("inlineAgentStep");
const reflectionTimer = document.getElementById("reflectionTimer");
const globalStatusPill = document.getElementById("globalStatusPill");

const devLogBox = document.getElementById("devLogBox");

const agentLauncher = document.getElementById("agentLauncher");
const agentBubble = document.getElementById("agentBubble");
const agentCloseBtn = document.getElementById("agentCloseBtn");
const agentCurrentText = document.getElementById("agentCurrentText");
const agentLog = document.getElementById("agentLog");
const agentLogo = document.getElementById("agentLogo");

const speechKeyMeta = document.querySelector('meta[name="azure-speech-key"]');
const speechRegionMeta = document.querySelector('meta[name="azure-speech-region"]');

const AZURE_SPEECH_KEY = speechKeyMeta?.content || "";
const AZURE_SPEECH_REGION = speechRegionMeta?.content || "";

let questions = [];
let currentQuestionIndex = 0;
let isRecording = false;
let reflectionInterval = null;
let lastWorkflowDecision = null;
let speechRecognizer = null;
let azureSpeechTranscript = "";

let agentHistory = [
  {
    agent: "WorkflowAgent",
    title: "Ready",
    message: "Waiting for your PDF upload.",
    status: "waiting"
  }
];

function logDev(message) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  console.log(message);
  devLogBox.textContent = `${line}\n${devLogBox.textContent}`.trim();
}

function setGlobalStatus(status, label) {
  globalStatusPill.textContent = label;
  globalStatusPill.className = `status-pill ${status}`;
}

function setQuestionStep(text) {
  questionStep.textContent = text;
}

function setAgentCurrent(message) {
  agentCurrentText.textContent = message;
  inlineAgentStep.textContent = message;
  logDev(`[Agent Current] ${message}`);
}

function renderAgentLog() {
  agentLog.innerHTML = "";
  const items = agentHistory.slice().reverse();

  items.forEach((entry) => {
    const item = document.createElement("div");
    item.className = "agent-log-item";
    item.innerHTML = `
      <div class="agent-log-dot ${entry.status}"></div>
      <div>
        <div style="font-size:0.92rem;font-weight:700;margin-bottom:2px;">${entry.agent}: ${entry.title}</div>
        <div style="color:#6b7280;font-size:0.88rem;">${entry.message}</div>
      </div>
    `;
    agentLog.appendChild(item);
  });
}

function addAgentLog(agent, title, message, status = "done") {
  const entry = { agent, title, message, status };
  agentHistory.push(entry);
  if (agentHistory.length > 14) {
    agentHistory = agentHistory.slice(agentHistory.length - 14);
  }
  renderAgentLog();
  logDev(`[${agent}] ${title} - ${message}`);
}

function openAgentBubble() {
  agentBubble.classList.add("open");
}

function closeAgentBubble() {
  agentBubble.classList.remove("open");
}

function resetAgentState() {
  agentHistory = [
    {
      agent: "WorkflowAgent",
      title: "Ready",
      message: "Waiting for your PDF upload.",
      status: "waiting"
    }
  ];
  setAgentCurrent("Idle. Waiting for your PDF.");
  renderAgentLog();
  setGlobalStatus("idle", "Idle");
}

function clearReflectionTimer() {
  if (reflectionInterval) {
    clearInterval(reflectionInterval);
    reflectionInterval = null;
  }
  reflectionTimer.textContent = "Not started";
}

function startReflectionCountdown(decision) {
  clearReflectionTimer();

  let remaining = REFLECTION_SECONDS;
  reflectionTimer.textContent = `${remaining}s remaining`;

  reflectionInterval = setInterval(() => {
    remaining -= 1;
    reflectionTimer.textContent = `${remaining}s remaining`;

    if (remaining <= 0) {
      clearReflectionTimer();
      applyDecisionAfterReflection(decision);
    }
  }, 1000);
}

function applyDecisionAfterReflection(decision) {
  if (!decision) return;

  logDev(`[WorkflowAgent] Applying post-reflection action: ${decision.action}`);

  if (decision.action === "advance" || decision.action === "reveal_and_move") {
    if (currentQuestionIndex < questions.length - 1) {
      currentQuestionIndex += 1;
      updateCurrentQuestion();
      renderQuestionCard();
      transcriptBox.textContent = "Transcript will appear here.";
      resetEvaluationUI();
      setQuestionStep("Ready");
      setAgentCurrent("WorkflowAgent moved to the next question.");
      addAgentLog("WorkflowAgent", "Moved forward", "Loaded the next question after reflection.", "done");
    } else {
      setQuestionStep("Completed");
      setAgentCurrent("Study session completed.");
      addAgentLog("WorkflowAgent", "Session complete", "No more questions remain.", "done");
    }
  }

  if (decision.action === "hint_retry") {
    transcriptBox.textContent = "Retry the same question and answer again.";
    setQuestionStep("Retry");
    setAgentCurrent("WorkflowAgent allows one retry with a hint.");
    addAgentLog("WorkflowAgent", "Retry enabled", "You may retry this question once after reflection.", "waiting");
  }
}

function renderQuestionCard() {
  if (questions.length === 0) {
    currentQuestion.textContent = "Upload a PDF to generate your first question.";
    questionCounter.textContent = "0 / 0";
    questionTopic.textContent = "No topic";
    setQuestionStep("Waiting");
    return;
  }

  const q = questions[currentQuestionIndex];
  currentQuestion.textContent = q.question || "No question available.";
  questionCounter.textContent = `${currentQuestionIndex + 1} / ${questions.length}`;
  questionTopic.textContent = q.topic || "General";
}

function updateCurrentQuestion() {
  renderQuestionCard();
}

function resetEvaluationUI() {
  statusBadge.textContent = "Waiting for evaluation";
  statusBadge.className = "status-chip neutral";
  scoreBox.textContent = "Score and decision will appear here.";
  feedbackBox.textContent = "Feedback and hint will appear here.";
}

function resetAllUI() {
  uploadStatus.textContent = "No file uploaded yet.";
  summaryBox.textContent = "Summary will appear here.";
  transcriptBox.textContent = "Transcript will appear here.";
  questions = [];
  currentQuestionIndex = 0;
  isRecording = false;
  lastWorkflowDecision = null;
  azureSpeechTranscript = "";
  renderQuestionCard();
  resetEvaluationUI();
  clearReflectionTimer();
  resetAgentState();
}

function getCurrentQuestion() {
  if (!questions.length) return null;
  return questions[currentQuestionIndex];
}

function createSpeechRecognizer() {
  if (!window.SpeechSDK) {
    throw new Error("Azure Speech SDK is not loaded.");
  }

  if (!AZURE_SPEECH_KEY || !AZURE_SPEECH_REGION) {
    throw new Error("Azure Speech key or region is missing.");
  }

  const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION
  );
  speechConfig.speechRecognitionLanguage = "en-US";

  const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();

  return new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
}

async function evaluateAndDecide(transcript) {
  const current = getCurrentQuestion();
  if (!current) return;

  openAgentBubble();
  setGlobalStatus("running", "Evaluating");
  setQuestionStep("Evaluating");
  setAgentCurrent("CoachAgent is evaluating your answer.");
  addAgentLog("CoachAgent", "Evaluating answer", "Checking concept coverage against the expected answer.", "running");

  const coachPayload = {
    questionId: current.id,
    topic: current.topic,
    question: current.question,
    transcript,
    idealAnswer: current.idealAnswer,
    keywords: current.keywords || [],
    sourceChunkIds: current.sourceChunkIds || []
  };

  try {
    const coachResponse = await fetch(`${BACKEND_BASE}/evaluate/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(coachPayload)
    });

    const coachResult = await coachResponse.json();

    if (!coachResponse.ok) {
      feedbackBox.textContent = coachResult.detail || "Evaluation failed.";
      setQuestionStep("Error");
      setGlobalStatus("idle", "Error");
      setAgentCurrent("CoachAgent evaluation failed.");
      addAgentLog("CoachAgent", "Evaluation failed", coachResult.detail || "Unknown error.", "waiting");
      return;
    }

    setAgentCurrent("WorkflowAgent is deciding the next step.");
    addAgentLog("WorkflowAgent", "Decision in progress", "Reading evaluation result and choosing the next action.", "running");

    const workflowPayload = {
      question: current,
      coachResult
    };

    const workflowResponse = await fetch(`${BACKEND_BASE}/workflow/decide`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(workflowPayload)
    });

    const workflowResult = await workflowResponse.json();

    if (!workflowResponse.ok) {
      feedbackBox.textContent = workflowResult.detail || "Workflow decision failed.";
      setQuestionStep("Error");
      setGlobalStatus("idle", "Error");
      setAgentCurrent("WorkflowAgent decision failed.");
      addAgentLog("WorkflowAgent", "Decision failed", workflowResult.detail || "Unknown error.", "waiting");
      return;
    }

    const decision = workflowResult.decision;
    lastWorkflowDecision = decision;

    statusBadge.textContent = decision.action;
    statusBadge.className =
      decision.action === "advance"
        ? "status-chip good"
        : decision.action === "hint_retry"
        ? "status-chip partial"
        : "status-chip weak";

    scoreBox.textContent =
      `Score: ${coachResult.score}\nRecommendation: ${coachResult.recommendation}`;

    feedbackBox.textContent =
      `${coachResult.feedback}\n\nMissing concepts: ${(coachResult.missingConcepts || []).join(", ") || "None"}\n\nNext step: ${decision.messageToUser}`;

    setQuestionStep("Reflect");
    setGlobalStatus("done", "Reviewed");
    setAgentCurrent(`WorkflowAgent decided: ${decision.action}`);
    addAgentLog("WorkflowAgent", "Decision complete", decision.messageToUser, "done");

    startReflectionCountdown(decision);
  } catch (error) {
    logDev(`Evaluate/Workflow error: ${error}`);
    feedbackBox.textContent = "Could not connect to backend.";
    setQuestionStep("Error");
    setGlobalStatus("idle", "Error");
    setAgentCurrent("Backend connection failed.");
    addAgentLog("WorkflowAgent", "Connection error", "Could not reach evaluation or workflow endpoint.", "waiting");
  }
}

agentLauncher.addEventListener("click", () => {
  agentBubble.classList.toggle("open");
});

agentCloseBtn.addEventListener("click", () => {
  closeAgentBubble();
});

document.addEventListener("click", (event) => {
  const clickedInsideBubble = agentBubble.contains(event.target);
  const clickedLauncher = agentLauncher.contains(event.target);
  if (!clickedInsideBubble && !clickedLauncher) {
    closeAgentBubble();
  }
});

agentLogo.addEventListener("error", () => {
  agentLauncher.classList.add("has-fallback");
  agentLogo.style.display = "none";
});

processBtn.addEventListener("click", async () => {
  const file = pdfFile.files[0];

  if (!file) {
    uploadStatus.textContent = "Please upload a PDF first.";
    openAgentBubble();
    setAgentCurrent("No PDF selected.");
    addAgentLog("WorkflowAgent", "Upload blocked", "Please choose a PDF first.", "waiting");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    uploadStatus.textContent = "Only PDF files are allowed.";
    openAgentBubble();
    setAgentCurrent("Invalid file type.");
    addAgentLog("WorkflowAgent", "Upload blocked", "Only PDF files are allowed.", "waiting");
    return;
  }

  setGlobalStatus("running", "Processing");
  setQuestionStep("Preparing");
  processBtn.disabled = true;
  processBtn.textContent = "Processing...";
  uploadStatus.textContent = "Uploading PDF...";
  summaryBox.textContent = "Waiting for backend response...";
  transcriptBox.textContent = "Transcript will appear here.";
  questions = [];
  currentQuestionIndex = 0;
  renderQuestionCard();
  resetEvaluationUI();
  clearReflectionTimer();

  openAgentBubble();
  resetAgentState();
  setAgentCurrent("WorkflowAgent is starting your study session.");
  addAgentLog("WorkflowAgent", "Session started", `Received file: ${file.name}`, "running");

  const formData = new FormData();
  formData.append("pdf", file);
  formData.append("instruction", instruction.value || "");

  const step1 = setTimeout(() => {
    setAgentCurrent("WorkflowAgent is saving your PDF.");
    addAgentLog("WorkflowAgent", "Saving PDF", "Storing uploaded file locally.", "running");
  }, 300);

  const step2 = setTimeout(() => {
    setAgentCurrent("WorkflowAgent is extracting text from your PDF.");
    addAgentLog("WorkflowAgent", "Extracting content", "Reading lecture text page by page.", "running");
  }, 900);

  try {
    const response = await fetch(`${BACKEND_BASE}/upload/`, {
      method: "POST",
      body: formData
    });

    clearTimeout(step1);
    clearTimeout(step2);

    const result = await response.json();

    if (!response.ok) {
      uploadStatus.textContent = result.detail || "Upload failed.";
      summaryBox.textContent = "Upload failed.";
      setQuestionStep("Error");
      setGlobalStatus("idle", "Error");
      setAgentCurrent("Upload failed.");
      addAgentLog("WorkflowAgent", "Upload failed", result.detail || "Unknown error.", "waiting");
      return;
    }

    uploadStatus.textContent = `Uploaded successfully: ${result.filename}`;
    summaryBox.textContent = result.summary || "Summary generation failed.";

    questions = Array.isArray(result.questions) ? result.questions : [];
    currentQuestionIndex = 0;
    renderQuestionCard();

    setQuestionStep("Ready");
    setGlobalStatus("done", "Ready");
    setAgentCurrent("ContentAgent finished summary and question generation.");
    addAgentLog("ContentAgent", "Summary ready", "AI summary generated from extracted lecture text.", "done");
    addAgentLog("ContentAgent", "Questions ready", `Generated ${questions.length} study question(s).`, "done");

    logDev(`Returned questions: ${JSON.stringify(result.questions || []).slice(0, 1000)}`);
    logDev(`Question count: ${result.questions?.length ?? 0}`);
  } catch (error) {
    logDev(`Upload error: ${error}`);
    uploadStatus.textContent = "Could not connect to backend.";
    summaryBox.textContent = "Connection to backend failed.";
    setQuestionStep("Error");
    setGlobalStatus("idle", "Error");
    setAgentCurrent("Backend connection failed.");
    addAgentLog("WorkflowAgent", "Connection error", "Could not reach backend API.", "waiting");
  } finally {
    processBtn.disabled = false;
    processBtn.textContent = "Process PDF";
  }
});

resetBtn.addEventListener("click", () => {
  pdfFile.value = "";
  instruction.value = "";
  resetAllUI();
});

prevQuestionBtn.addEventListener("click", () => {
  if (questions.length === 0) return;
  currentQuestionIndex = (currentQuestionIndex - 1 + questions.length) % questions.length;
  updateCurrentQuestion();
  openAgentBubble();
  setAgentCurrent("WorkflowAgent moved to the previous question.");
  addAgentLog("WorkflowAgent", "Moved backward", "Loaded the previous question.", "done");
});

nextQuestionBtn.addEventListener("click", () => {
  if (questions.length === 0) return;
  currentQuestionIndex = (currentQuestionIndex + 1) % questions.length;
  updateCurrentQuestion();
  openAgentBubble();
  setAgentCurrent("WorkflowAgent moved to the next question.");
  addAgentLog("WorkflowAgent", "Moved forward", "Loaded the next question.", "done");
});

startRecordBtn.addEventListener("click", async () => {
  if (!questions.length) return;

  try {
    if (speechRecognizer) {
      speechRecognizer.close();
      speechRecognizer = null;
    }

    azureSpeechTranscript = "";
    speechRecognizer = createSpeechRecognizer();

    speechRecognizer.recognizing = (_, event) => {
      const partial = event.result?.text || "";
      if (partial) {
        transcriptBox.textContent = partial;
        logDev(`Recognizing: ${partial}`);
      }
    };

    speechRecognizer.recognized = (_, event) => {
      const finalText = event.result?.text || "";
      if (finalText) {
        azureSpeechTranscript = finalText;
        transcriptBox.textContent = finalText;
        logDev(`Recognized: ${finalText}`);
      }
    };

    speechRecognizer.canceled = (_, event) => {
      logDev(`Speech canceled: ${event.errorDetails || event.reason}`);
      setQuestionStep("Error");
      setGlobalStatus("idle", "Error");
      transcriptBox.textContent = `Speech canceled: ${event.errorDetails || event.reason}`;
    };

    speechRecognizer.sessionStarted = () => {
      logDev("Azure Speech session started.");
    };

    speechRecognizer.sessionStopped = () => {
      logDev("Azure Speech session stopped.");
    };

    isRecording = true;
    clearReflectionTimer();
    setGlobalStatus("running", "Recording");
    setQuestionStep("Recording");
    transcriptBox.textContent = "Listening...";
    openAgentBubble();
    setAgentCurrent("Azure Speech is listening to your spoken answer.");
    addAgentLog("Azure Speech", "Recording started", "Listening for your answer.", "running");

    speechRecognizer.startContinuousRecognitionAsync(
      () => {
        logDev("Continuous recognition started.");
      },
      (err) => {
        logDev(`Speech start error: ${err}`);
        transcriptBox.textContent = `Could not start speech recognition: ${err}`;
        setQuestionStep("Error");
        setGlobalStatus("idle", "Error");
      }
    );
  } catch (error) {
    logDev(`Microphone/Speech init error: ${error}`);
    transcriptBox.textContent = `Could not initialize Azure Speech: ${error}`;
    setQuestionStep("Error");
    setGlobalStatus("idle", "Error");
  }
});

stopRecordBtn.addEventListener("click", async () => {
  if (!questions.length || !isRecording || !speechRecognizer) return;

  isRecording = false;
  setGlobalStatus("running", "Transcribing");
  setQuestionStep("Transcribing");
  openAgentBubble();
  setAgentCurrent("Azure Speech is finalizing your transcript.");
  addAgentLog("Azure Speech", "Stopping recognition", "Finalizing transcript from microphone input.", "running");

  await new Promise((resolve, reject) => {
    speechRecognizer.stopContinuousRecognitionAsync(
      () => resolve(),
      (err) => reject(err)
    );
  }).catch((err) => {
    logDev(`Speech stop error: ${err}`);
    transcriptBox.textContent = `Could not stop speech recognition: ${err}`;
    setQuestionStep("Error");
    setGlobalStatus("idle", "Error");
  });

  if (!azureSpeechTranscript.trim()) {
    transcriptBox.textContent = "No transcript returned.";
    setQuestionStep("Error");
    setGlobalStatus("idle", "Error");
    addAgentLog("Azure Speech", "No transcript", "No recognized speech was returned.", "waiting");
    return;
  }

  setAgentCurrent("Azure Speech finished transcription.");
  addAgentLog("Azure Speech", "Transcript ready", "The spoken answer was converted into text.", "done");

  await evaluateAndDecide(azureSpeechTranscript);
});

resetAgentState();
renderQuestionCard();
resetEvaluationUI();
clearReflectionTimer();