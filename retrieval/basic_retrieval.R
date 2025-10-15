# basic_retrieval.R
# Read in file, subset, prompt and get answer.

# Formatting
QUESTION_DELIMITER_regex <- "^Q:"
ANSWER_DELIMITER_regex <- "^A:"
ENTRY_DELIMITER_regex <- "^---"
#formatted_pair_delimiter <- paste("^", ENTRY_DELIMITER_regex, sep = "")

# Configuration
FILE_DIRECTORY_path <- ""
SUBSET_SIZE_int <- 2
FILE_WITH_QUESTIONS <- "questions.txt"
FILE_PATTERNS <- list()

REPO_DIRECTORY_path <- system("git rev-parse --show-toplevel", intern = TRUE)
is_custom_directory_bool <- nzchar(FILE_DIRECTORY_path)
if (!is_custom_directory_bool) {
  RETRIEVAL_FILE_DIRECTORY_path <- file.path(REPO_DIRECTORY_path, "retrieval")
}

FILE_PATHS <- file.path(
  RETRIEVAL_FILE_DIRECTORY_path,
  FILE_WITH_QUESTIONS
)

questions_file_data <- readLines(FILE_PATHS)
#object.size(questions_file_data)
delimiter_lines_indexes <- grep(ENTRY_DELIMITER_regex, questions_file_data)
indexes_for_pairs <- c(1)
for (index in delimiter_lines_indexes) {
  message("Current index: ", index)

  number_of_delimiters <- length(delimiter_lines_indexes)
  is_last_delimiter_index <- index == delimiter_lines_indexes[number_of_delimiters]
  if (is_last_delimiter_index) {
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
  in_question_block <- FALSE
  first_line_of_pair <- indexes_for_pairs[index, 1]
  last_line_of_pair <- indexes_for_pairs[index, 2]
  question_answer_pair <- questions_file_data[first_line_of_pair:last_line_of_pair]

  for (line in question_answer_pair) {
    message("==========================")
    #message("Current line:")
    #message(line)
    is_question_delimiter_line <- grepl(QUESTION_DELIMITER_regex, line)
    is_answer_delimiter_line <- grepl(ANSWER_DELIMITER_regex, line)
    if (is_question_delimiter_line) {
      in_question_block <- TRUE
      question_content <- gsub("^Q:", "", line)
      qa_dataframe[index, "question"] <- question_content
      message("In question block value: ", as.character(in_question_block))
      next
    }

    if (is_answer_delimiter_line) {
      in_question_block <- FALSE
      question_content <- gsub("^A:", "", line)
      qa_dataframe[index, "answer"] <- question_content
      message("In question block value: ", as.character(in_question_block))
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

    message("==========================")

  }

}

random_questions_idx <- sample(
  nrow(qa_dataframe),
  SUBSET_SIZE_int,
  replace = FALSE
)

random_subset_df <- qa_dataframe[random_questions_idx, ]
stopifnot(
  "Rows should be same as number sampled." =
    SUBSET_SIZE_int == nrow(random_subset_df)
)
random_subset_df$user_answers <- rep(NA, nrow(random_subset_df))

for (row_idx in 1:SUBSET_SIZE_int) {
  message("--------------------------")
  exercise_pair <- random_subset_df[row_idx, ]
  message("Question ", row_idx, " out of ", SUBSET_SIZE_int)
  #message("---")
  message(exercise_pair$question)
  #message(exercise_pair[1, 1])
  #message("---")
  user_answer <- readline(prompt = "")
  random_subset_df[row_idx, "user_answers"] <- user_answer
  #message("--------------------------")
}
