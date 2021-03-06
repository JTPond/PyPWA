"""
Actual process objects are defined here
"""
__author__ = "Mark Jones"
__credits__ = ["Mark Jones"]
__license__ = "MIT"
__version__ = "2.0.0"
__maintainer__ = "Mark Jones"
__email__ = "maj@jlab.org"
__status__ = "Beta0"

import multiprocessing
import numpy
import warnings
import logging


class AbstractProcess(multiprocessing.Process):
    """Abstract class extending multiprocessing.Process
    Attributes:
        _looping  Defines if if to continue _looping, is set to true
        daemon   If process is bool, is set to true.
    """

    _looping = True
    daemon = True

    def __init__(self):
        super(AbstractProcess, self).__init__()

    def run(self):
        """Main loop for Processes"""
        self.setup()
        while self._looping:
            try:
                self.processing()
            except KeyboardInterrupt:
                return 0
        return 0

    def setup(self):
        """Initial setup for processes"""
        raise NotImplementedError("Class %s doesn't implement aMethod()" % self.__class__.__name__)

    def processing(self):
        """Actual function for processing"""
        raise NotImplementedError("Class %s doesn't implement aMethod()" % self.__class__.__name__)


class RejectionAcceptanceAmplitude(AbstractProcess):
    """Acceptance Rejection Process
    Args:
        amplitude_function (function): Users amplitude function
        setup_function (function): Setup function
        data (dict): Dictionary of numpy arrays
        parameters (dict): Parameters used to calculate
        send (Pipe): Pipe to use to send data back to the main thread
        the_id (int): id of the thread
    """

    def __init__(self, amplitude_function, setup_function, data, parameters, send, the_id):
        super(RejectionAcceptanceAmplitude, self).__init__()
        self._amplitude_function = amplitude_function
        self._setup_function = setup_function
        self._data = data
        self._parameters = parameters
        self._send = send
        self._id = the_id
        warnings.warn("RejectionAcceptanceAmplitude is being depreciated, use LoopingIntensity instead",
                      DeprecationWarning)

    def setup(self):
        """Runs the setup function"""
        self._setup_function()

    def processing(self):
        """Processes data"""
        self._send.send([self._id, self._amplitude_function(self._data, self._parameters)])
        self._looping = False


class LoopingIntensity(AbstractProcess):

    def __init__(self, amplitude_function, setup_function, data, send, receive, the_id=None):
        super(LoopingIntensity).__init__()
        self.amplitude = amplitude_function
        self.setup_function = setup_function
        self.data = data
        self.send = send
        self.receive = receive
        if isinstance(the_id, int):
            self.the_id = the_id
            self.tracked = True
        else:
            self.tracked = False

    def _pipe_send(self, data):
        self.send.send(data)

    def _pipe_recv(self):
        return self.receive.recv()

    def setup(self):
        self.setup_function()

    def processing(self):
        received = self._pipe_recv()
        if received == "DIE":
            self._looping = False
        else:
            intensity = self.amplitude(self.data, received)
            if self.tracked:
                values = [self.the_id, intensity]
            else:
                values = intensity
            self._pipe_send(values)


class AbstractLikelihoodAmplitude(AbstractProcess):
    """Abstract Likelihood that handles all the processing except the likelihood
    Attributes:
        setup_function (function): the function to run before calculation
        send (multiprocessing.Pipe): The pipe to send information back with
        receive (multiprocessing.Pipe): The pipe to receive parameters back from
    """

    def __init__(self, setup_function, send, receive):
        super(AbstractLikelihoodAmplitude, self).__init__()
        self._setup_function = setup_function
        self._send = send
        self._receive = receive

    def setup(self):
        """Runs the setup function"""
        self._setup_function()

    def processing(self):
        """Processes the data"""
        parameters = self._receive.recv()
        if parameters == "DIE":
            self._looping = False
        else:
            result = self.likelihood(parameters)
            self._send.send(result)

    def likelihood(self, parameters):
        raise NotImplementedError("Class %s doesn't implement aMethod()" % self.__class__.__name__)


class ExtendedLikelihoodAmplitude(AbstractLikelihoodAmplitude):
    """Likelihood Estimation Process
    Args:
        amplitude_function (function): Users amplitude function
        setup_function (function): Setup function
        processed (float): Constant for likelihood, 1/Generated_length
        data (dict): Dictionary of numpy arrays
        accepted (dict): Dictionary of numpy arrays with Accepted Monte Carlo
        send (Pipe): Pipe to use to send data back to the main thread
        receive (Pipe): Pipe to receive parameters with
    """

    def __init__(self, amplitude_function, setup_function, processed, data, accepted, send, receive):
        super(ExtendedLikelihoodAmplitude, self).__init__(setup_function, send, receive)
        self._amplitude_function = amplitude_function
        self._processed = processed
        self._data = data
        self._accepted = accepted
        numpy.seterr(divide="raise")
        self._fallback = False

    def likelihood(self, parameters):
        """Calculates the likelihood function
        Args:
            parameters (dict): dictionary of the arguments to be sent to the function
        """
        if not self._fallback:
            try:
                processed_data = self._amplitude_function(self._data["data"], parameters)
                processed_accepted = self._amplitude_function(self._accepted["data"], parameters)
                return -(numpy.sum(self._data["QFactor"] * numpy.log(processed_data))) + \
                        (self._processed * numpy.sum(processed_accepted))
            except FloatingPointError:
                print("Found zeros in data, falling back to masked arrays.")
                self._fallback = True
                processed_data = numpy.ma.masked_equal(self._amplitude_function(self._data["data"], parameters), 0)
                processed_accepted = numpy.ma.masked_equal(self._amplitude_function(self._accepted["data"], parameters), 0)
                return -(numpy.ma.sum(self._data["QFactor"] * numpy.ma.log(processed_data))) + \
                        (self._processed * numpy.ma.sum(processed_accepted))
        else:
            processed_data = numpy.ma.masked_equal(self._amplitude_function(self._data["data"], parameters), 0)
            processed_accepted = numpy.ma.masked_equal(self._amplitude_function(self._accepted["data"], parameters), 0)
            return -(numpy.ma.sum(self._data["QFactor"] * numpy.ma.log(processed_data))) + \
                    (self._processed * numpy.ma.sum(processed_accepted))


class UnextendedLikelihoodAmplitude(AbstractLikelihoodAmplitude):
    """Likelihood Estimation Process
    Args:
        amplitude_function (function): Users amplitude function
        setup_function (function): Setup function
        data (dict): Dictionary of numpy arrays
        send (Pipe): Pipe to use to send data back to the main thread
        receive (Pipe): Pipe to receive parameters with
    """

    def __init__(self, amplitude_function, setup_function, data, send, receive):
        super(UnextendedLikelihoodAmplitude, self).__init__(setup_function, send, receive)
        self._amplitude_function = amplitude_function
        self._data = data
        self._fallback = False
        numpy.seterr(divide='raise')

    def likelihood(self, parameters):
        """Calculates the likelihood function
        Args:
            parameters (dict): dictionary of the arguments to be sent to the function
        """
        if not self._fallback:
            try:
                processed_data = self._amplitude_function(self._data["data"], parameters)
                return -(numpy.sum(self._data["QFactor"] * self._data["BinN"] * numpy.log(processed_data)))
            except FloatingPointError:
                self._fallback = True
                print("Found Zeros in Data, falling back to masked")
                processed_data = numpy.ma.masked_equal(self._amplitude_function(self._data["data"], parameters), 0)
                return -(numpy.ma.sum(self._data["QFactor"] * self._data["BinN"] * numpy.ma.log(processed_data)))
        else:
            processed_data = numpy.ma.masked_equal(self._amplitude_function(self._data["data"], parameters), 0)
            return -(numpy.ma.sum(self._data["QFactor"] * self._data["BinN"] * numpy.ma.log(processed_data)))


class ChiSquared(AbstractLikelihoodAmplitude):

    def __init__(self, amplitude_function, setup_function, data, send, receive):
        super(ChiSquared, self).__init__(setup_function, send, receive)
        self._amplitude_function = amplitude_function
        self._data = data

    def likelihood(self, parameters):
        processed_data = self._amplitude_function(self._data["data"], parameters)
        return numpy.sum(((processed_data - self._data["BinN"])**2) / self._data["BinN"])
