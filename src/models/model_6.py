from argparse import ArgumentParser

from keras import Input, Model
from keras.layers import Dense, BatchNormalization, Embedding, Reshape, Concatenate

from src.encoder.numeric_log import NumericLog
from src.models.model_builder import ModelBuilder
from src.models.preprocessor import Preprocessor
from src.utils.calculate_class_weights import calculate_class_weights
from src.utils.f1_score import precision, recall, f1
from src.utils.logging.callback_builder import CallbackBuilder
from src.utils.logging.callbacks.config_logger import ConfigLogger
from src.utils.logging.callbacks.csv_logger import CsvLogger
from src.utils.logging.callbacks.csv_plotter import CsvPlotter
from src.utils.logging.callbacks.model_saver import ModelSaver
from src.utils.settings import Settings


class Model6Builder(ModelBuilder):
    def __init__(self):
        super().__init__()

        self.required_inputs.append('headline_numeric_log')
        self.required_inputs.append('article_numeric_log')

    def __call__(self):
        super().check_required()

        headline_numeric_log = self.inputs['headline_numeric_log']
        article_numeric_log = self.inputs['article_numeric_log']

        headline_numeric_log_input = Input(shape=(1,), name='headline_log_representation_input')
        headline_numeric_log_embedding = Embedding(headline_numeric_log.max_log_value() + 1,
                                                   self.parameters['headline_log_representation_embedding_dimensions'])(
            headline_numeric_log_input)
        headline_numeric_log_reshape = Reshape((self.parameters['headline_log_representation_embedding_dimensions'],))(
            headline_numeric_log_embedding)

        article_numeric_log_input = Input(shape=(1,), name='article_numeric_log_input')
        article_numeric_log_embedding = Embedding(article_numeric_log.max_log_value() + 1,
                                                  self.parameters['article_log_representation_embedding_dimensions'])(
            article_numeric_log_input)
        article_numeric_log_reshape = Reshape((self.parameters['article_log_representation_embedding_dimensions'],))(
            article_numeric_log_embedding)

        concat = Concatenate()([headline_numeric_log_reshape, article_numeric_log_reshape])
        fully_connected = Dense(self.parameters['fully_connected_dimensions'],
                                activation=self.parameters['fully_connected_activation'])(concat)
        batch_normalization = BatchNormalization()(fully_connected)
        main_output = Dense(1, activation='sigmoid', name='output')(batch_normalization)

        model = Model(inputs=[headline_numeric_log_input, article_numeric_log_input],
                      outputs=[main_output],
                      name=self.model_identifier)

        model.compile(loss=self.parameters['loss'],
                      optimizer=self.parameters['optimizer'],
                      metrics=['accuracy', precision, recall, f1])

        return model

    @property
    def model_identifier(self):
        return 'model_6'


def train():
    settings = Settings()

    batch_size = settings.get_training_parameters('batch_size')
    epochs = settings.get_training_parameters('epochs')
    max_headline_length = settings.get_training_parameters('max_headline_length')
    max_article_length = settings.get_training_parameters('max_article_length')

    headline_numeric_log = NumericLog(max_headline_length)
    article_numeric_log = NumericLog(max_article_length)

    model_builder = Model6Builder() \
        .set_input('headline_numeric_log', headline_numeric_log) \
        .set_input('article_numeric_log', article_numeric_log)

    model = model_builder()

    preprocessor = Preprocessor(model)
    preprocessor.set_encoder('headline_numeric_log', headline_numeric_log)
    preprocessor.set_encoder('article_numeric_log', article_numeric_log)

    preprocessor.load_data(['headline_log_representation', 'article_log_representation', 'is_top_submission'])
    training_input = [preprocessor.training_data['headline_log_representation'],
                      preprocessor.training_data['article_log_representation']]
    validation_input = [preprocessor.validation_data['headline_log_representation'],
                        preprocessor.validation_data['article_log_representation']]
    training_output = [preprocessor.training_data['is_top_submission']]
    validation_output = [preprocessor.validation_data['is_top_submission']]

    class_weights = calculate_class_weights(preprocessor.training_data['is_top_submission'],
                                            [ol.name for ol in model.output_layers])

    callbacks = CallbackBuilder(model, [CsvLogger, CsvPlotter, ConfigLogger, ModelSaver])()

    model.fit(training_input, training_output, batch_size=batch_size, epochs=epochs,
              callbacks=callbacks, validation_data=(validation_input, validation_output), class_weight=class_weights)
