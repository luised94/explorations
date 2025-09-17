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
indexes_for_pairs <- cbind(indexes_for_pairs, rep(0, length(indexes_for_pairs)))

for (index in 1:nrow(indexes_for_pairs)) {
  is_odd <- index %% 2
  if ( is_odd ) {
    indexes_for_pairs[index, 2] <- indexes_for_pairs[index + 1, 1]

  }

}
is_odd <- as.logical(1:nrow(indexes_for_pairs) %% 2)
indexes_for_pairs <- indexes_for_pairs[is_odd, ]
qa_dataframe <- data.frame(
  question = NA,
  answer = NA
)

for (index in 1:nrow(indexes_for_pairs)){
  message("Handling pair: ", index)
  first_line_of_pair <- indexes_for_pairs[index, 1]
  last_line_of_pair <- indexes_for_pairs[index, 2]
  question_answer_pair <- questions_file_data[first_line_of_pair:last_line_of_pair]

  in_question_block <- FALSE
  for (line in question_answer_pair) {
    message("==========================")
    message("Current line:")
    message(line)
    if (grepl("^Q:", line)) {
      in_question_block <- TRUE
      question_content <- gsub("^Q:", "", line)
      qa_dataframe[index, "question"] <- question_content
      next
    }

    if (grepl("^A:", line)) {
      in_question_block <- FALSE
      question_content <- gsub("^A:", "", line)
      qa_dataframe[index, "answer"] <- question_content
      next
    }

    if (in_question_block) {
      qa_dataframe[index, "question"] <- paste(
        qa_dataframe[index, "question"],
        "\n",
        line
      )

    } else {
      qa_dataframe[index, "answer"] <- paste(
        qa_dataframe[index, "answer"],
        "\n",
        line
      )

    }
    message("In question block value: ", as.character(in_question_block))
    message("==========================")

  }

}

