# basic_retrieval.R
# Read in file, subset, prompt and get answer.

# Formatting
question_delimiter <- "Q:"
answer_delimiter <- "A:"
pair_delimiter <- "---"

FILE_WITH_QUESTIONS <- "questions.txt"
ROOT_DIRECTORY <- system("git rev-parse --show-toplevel", intern = TRUE)
RETRIEVAL_PROJECT_PATH <- file.path(ROOT_DIRECTORY, "retrieval")
FILE_PATH <- file.path(
  RETRIEVAL_PROJECT_PATH,
  FILE_WITH_QUESTIONS
)

questions_file_data <- readLines(FILE_PATH)
#object.size(questions_file_data)
formatted_pair_delimiter <- paste("^", pair_delimiter, sep = "")
delimiter_lines_indexes <- grep(formatted_pair_delimiter, questions_file_data)
indexes_for_pairs <- c(1)
for (index in delimiter_lines_indexes) {
  message("Current index: ", index)

  if ( index == delimiter_lines_indexes[length(delimiter_lines_indexes)]) {
    indexes_for_pairs <- c(indexes_for_pairs, index - 1)
    next
  }

  indexes_for_pairs <- c(indexes_for_pairs, index - 1, index + 1)
}


